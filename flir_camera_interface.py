## TODO:
## 1. When the "Live Data" button is OFF, enable a pushbutton that shows a popup Histogram of the current image.
##    It would really help to be able to zoom this histogram to check values.
## 2. Find out what "High Dynamic Range Mode" is on these cameras. Can we make use of it?
## 3. And what is "Exposure Compensation Auto" anyway? Currently it is set always on. Do we need to turn it off?
## 4. If you want to be able to set the FrameRate manually, you will first have to set the "FrameRateAuto" to "Off".
## 5. Allow a user to save filenames using the timestamps instead of the file_counter.
## 6. Consider capturing error messages and sending them into the outputbox. The relevant code would look like:
##        except Exception as err_msg:
##            self.outputbox.appendPlainText(err_msg)
## 7. Try connecting your FLIR microbolometer camera and see if it works with the Spinnaker library. If it doesn't, you will want to use the 
##    "Mono14" pixel format rather than "Mono16". With the latter, you will need to shift the image data down 2 bits (i.e. divide by 4) to 
##    get the correct 14-bit result.
## 8. Make another version of the interface based on two cameras operating simultaneously. Nice for UV-VIS or VIS-NIR dual camera use.
## 9. Currently the video saving is quite slow. Doing the saving inside the PySpin library would be much faster, but their examples only show
##    8 bit data. But maybe you can figure out how to save the raw bytestream, and then figure out how to decode the raw bytes from each file?
                
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtGui import QKeySequence, QIcon, QColor, QFont
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QMenuBar, QStatusBar,
                             QHBoxLayout, QAction, QDialog, QFrame, QFileDialog, QGroupBox, QRadioButton, QGridLayout,
                             QTabWidget, QLabel, QCheckBox, QSpinBox, QPlainTextEdit, QMessageBox, QErrorMessage,
                             QDoubleSpinBox, QDialogButtonBox, QLineEdit, QLabel, QDesktopWidget, QPushButton, QFormLayout)

## import the Qt5Agg figure canvas object, that binds figures to the Qt5Agg backend. It also inherits from QWidget.
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid1 import ImageGrid, make_axes_locatable
import matplotlib as mpl
mpl.rcParams['image.origin'] = 'lower'  ## set the lower left corner to be the (0,0) position for the image

import numpy
from numpy import (pi, array, asarray, linspace, indices, amin, amax, sqrt, exp, mean, std, nan, NaN,
                   logical_and, zeros, uint8, mgrid, ones, uint32, load, float32, where, arange, uint16,
                   logical_or, log, savez, empty, reshape, ndim, cos, rint, log2)
numpy.seterr(all='raise')
numpy.seterr(invalid='ignore')

import struct, time, os, sys
from imageio import imread, imsave
import PySpin
import flir_spin_library as fsl

## ===========================================================================================================
class MPLCanvas(FigureCanvas):
    def __init__(self, noaxis=False):
        ## setup the matplotlib Figure and Axis
        self.fig = Figure(figsize=(13,10))
        if not noaxis:
            self.ax = self.fig.add_subplot(111)
            #self.fig.subplots_adjust(left=0.125, right=0.9, bottom=0.1, top=0.9)
            self.fig.subplots_adjust(left=0.05, right=0.99, bottom=0.025, top=0.975)

        ## Initialization of the canvas
        FigureCanvas.__init__(self, self.fig)

        ## Define the widget as expandable.
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)

        ## Notify the system of the updated policy.
        FigureCanvas.updateGeometry(self)

## ===========================================================================================================
class MPLWidget(QWidget):
    def __init__(self, parent=None, noaxis=False):
        ## Initialization of the Qt MainWindow widget
        QWidget.__init__(self,parent)

        ## Set the canvas to the matplotlib widget.
        self.canvas = MPLCanvas(noaxis=noaxis)

        ## Create a navigation toolbar for our plot canvas.
        self.navi_toolbar = NavigationToolbar(self.canvas, self)

        ## Create a vertical box layout and add widgets to it.
        self.vbl = QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.vbl.addWidget(self.navi_toolbar)
        self.setLayout(self.vbl)

## ===========================================================================================================
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.resize(gui_width, gui_height)

        #self.setObjectName('MainWindow')
        self.image_counter = 0      ## the counter of the current image within the latest sequence
        self.navgs = 1              ## the number of frames to average for each display frame
        self.first_draw = True      ## is this the first time drawing Figure 1?
        self.bad = None             ## bad pixels image (boolean)
        self.cb = None              ## a place-holder for Figure1's colorbar object
        self.xalign = None          ## the relative x-displacement of image1 from image0
        self.yalign = None          ## the relative y-displacement of image1 from image0
        self.do_bkgd_subtraction = False
        self.file_counter = 0       ## counter for incrementing the filenames
        self.exposure = 10000
        self.binning = 1
        self.cam_bitdepth = 12 + uint16(log2(self.binning))      ## camera bit depth
        self.cam_saturation_level = (2**self.cam_bitdepth) - 1 - 7  ## why do we need '-7' here?!
        self.img_has_saturation = False
        self.outputbox = None       ## need to define this variable early to prevent error -- it gets redefined later
        self.cwd = os.getcwd()

        ## Fringe projection profilometry (FPP) stuff
        self.has_fpp = False        ## Is the FPP system activated?
        self.nphases = 4            ## the number of pattern images to use for estimating phase
        self.nfringes = 16          ## the number of fringes to project across the image
        self.phasenum = 0           ## the number of the current projection pattern (from 0 to [1-self.nphases])

        ## Liquid-crystal tunable filter (LCTF) stuff
        self.has_lctf = False
        self.lctf_wavelist = arange(420,730,10)     ## returns a list from 420 to 720 in increments of 10
        self.lctf_wave_counter = 0          ## counter for which element of wavelist is the current one
        self.lctf_currentwave = self.lctf_wavelist[self.lctf_wave_counter]    ## the current wavelength

        ## Make a custom colormap where the maximum value is changed from white to red.
        ## Why -8? I tried -7 and it wasn't enough. Note, however, that if the colorbar range are changed, then this 
        ## '-8' no longer is the best choice. How to fix?
        grey = cm.get_cmap('gray', 256)
        newcolors = grey(linspace(0, 1, self.cam_saturation_level))
        #newcolors[255,:] = array([1,0,0,1])      ## red color with alpha=1
        newcolors[-8:,:] = array([1,0,0,1])      ## red color with alpha=1
        self.satgrey = ListedColormap(newcolors)
        #print(self.satgrey(linspace(0,1,self.cam_saturation_level)))

        ## Define the image scale for each image -- we will need these for the manual controls on the colorbars of each image.
        self.image_vmin_str = 'Min'
        self.image_vmax_str = 'Max'

        ## Set the window background to a medium gray color.
        self.grey_palette = self.palette()
        self.grey_palette.setColor(self.backgroundRole(), QColor(225,225,225))
        self.setPalette(self.grey_palette)

        fileOpenAction = self.createAction("&Open File", self.fileOpen, QKeySequence.Open, "fileopen", "Load an image")
        fileSaveAction = self.createAction("&Save Image", self.fileSave, QKeySequence.Save, "filesave", "Save an image")
        videoSaveAction = self.createAction("Save &Video Sequence", self.save_video_sequence, QKeySequence.Paste, "videosave", "Save a video sequence")
        fileQuitAction = self.createAction("&Quit", self.close, "Ctrl+Q", "quit", "Close the application")

        self.mb = self.menuBar()
        self.mb.setObjectName('menubar')
        self.fileMenu = self.mb.addMenu('&File')
        self.addActions(self.fileMenu, (fileOpenAction, fileSaveAction, videoSaveAction, fileQuitAction))

        self.mainframe = QFrame(self)
        self.setCentralWidget(self.mainframe)
        self.mplwidget = MPLWidget()

        ## The QHBoxLayout for the image is needed to ensure that the image display will automatically stretch with the window geometry.
        self.hlt1 = QHBoxLayout()
        self.hlt1.addWidget(self.mplwidget)

        self.saturation_checkbox = QCheckBox('Paint saturated pixels red', self)
        self.saturation_checkbox.setChecked(True)
        self.saturation_checkbox.stateChanged.connect(self.saturationCheckChange)

        ## The outputbox object needs to go before camera initialization, so that any messages have a place to get printed.
        self.outputbox = QPlainTextEdit('')
        self.outputbox.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.initialize_camera()
        self.initialize_image_data()

        self.statusbar = QStatusBar()
        self.statusbar.setObjectName('statusbar')
        self.statusbar.setSizeGripEnabled(False)
        self.statusbar_label = QLabel(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')
        self.statusbar.addWidget(self.statusbar_label)
        self.setStatusBar(self.statusbar)

        self.live_checkbox = QCheckBox('Live Data', self)
        if (self.ncameras > 0):
            self.live_checkbox.setChecked(self.ncameras > 0)
        else:
            self.live_checkbox.setEnabled(False)
        self.live_checkbox.stateChanged.connect(self.liveDataChange)

        self.file_dir_label = QLabel('File directory:')
        self.file_prefix_label = QLabel('File prefix:')
        self.file_suffix_label = QLabel('File suffix:')
        self.file_dir_editbox = QLineEdit('')
        self.file_prefix_editbox = QLineEdit('image')
        self.file_suffix_editbox = QLineEdit('tif')

        self.file_dir_hlt = QHBoxLayout()
        self.file_dir_hlt.addWidget(self.file_dir_label)
        self.file_dir_hlt.addWidget(self.file_dir_editbox)

        self.file_prefix_hlt = QHBoxLayout()
        self.file_prefix_hlt.addWidget(self.file_prefix_label)
        self.file_prefix_hlt.addWidget(self.file_prefix_editbox)

        self.file_suffix_hlt = QHBoxLayout()
        self.file_suffix_hlt.addWidget(self.file_suffix_label)
        self.file_suffix_hlt.addWidget(self.file_suffix_editbox)

        self.save_nframes_label = QLabel('# video frames: ')
        self.save_nframes_spinbox = QSpinBox()
        self.save_nframes_spinbox.setRange(1,99999)
        self.save_nframes_spinbox.setValue(1)
        self.save_nframes_spinbox.setSingleStep(1)
        self.save_nframes_button = QPushButton('Save Frame(s)')
        self.save_nframes_button.clicked.connect(self.save_video_sequence)

        self.boldfont = QFont()
        self.boldfont.setBold(True)

        self.cam_label = QLabel('Camera Settings:')
        self.cam_label.setFont(self.boldfont)

        self.framerate_label = QLabel('Frame rate (Hz)')
        self.framerate_spinbox = QDoubleSpinBox()
        self.framerate_spinbox.setValue(self.framerate)
        self.framerate_spinbox.setSingleStep(1.0)
        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            self.framerate_spinbox.setRange(1.0,1000.0)
            self.framerate_spinbox.valueChanged.connect(self.frameRateChange)
        else:
            self.framerate_spinbox.setEnabled(False)
            self.framerate_label.setStyleSheet('color: rgba(125, 125, 125, 0);')

        self.exposure_label = QLabel('Exposure time (\u03bcs)')
        self.exposure_spinbox = QSpinBox()
        self.exposure_spinbox.setSingleStep(1000)
        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            self.exposure_spinbox.setRange(uint32(self.min_exposure),uint32(self.max_exposure))
            self.exposure_spinbox.valueChanged.connect(self.exposureChange)
        else:
            self.exposure_spinbox.setEnabled(False)
            self.exposure_label.setStyleSheet('color: rgba(125, 125, 125, 1);')
        self.exposure_spinbox.setValue(self.exposure)   ## note that the setValue() function has to come last in this block!

        #self.cam_gain_label = QLabel('Sensor gain (dB)')
        #self.cam_gain_spinbox = QSpinBox()
        #self.cam_gain_spinbox.setValue(int(rint(self.cam_gain)))
        #self.cam_gain_spinbox.setSingleStep(1)
        #if (self.ncameras > 0) and self.live_checkbox.isChecked():
        #    self.cam_gain_spinbox.setRange(1,20)
        #    self.cam_gain_spinbox.valueChanged.connect(self.gainChange)
        #else:
        #    self.cam_gain_spinbox.setEnabled(False)
        #    self.cam_gain_label.setStyleSheet('color: rgba(125, 125, 125, 1);')

        self.cam_navgs_label = QLabel('Frame Averages (Navgs)')
        self.cam_navgs_spinbox = QSpinBox()
        self.cam_navgs_spinbox.setValue(self.navgs)
        self.cam_navgs_spinbox.setSingleStep(1)
        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            self.cam_navgs_spinbox.setRange(1,100)
            self.cam_navgs_spinbox.valueChanged.connect(self.navgsChange)
        else:
            self.cam_navgs_spinbox.setEnabled(False)
            self.cam_navgs_label.setStyleSheet('color: rgba(125, 125, 125, 1);')    ## grey-out the font when disabled

        self.draw_fig1()

        self.cbar_fix_label = QLabel('Limit image display range (min,max):')
        self.cbar_fixmin_editbox = QLineEdit('Min')
        self.cbar_fixmax_editbox = QLineEdit('Max')
        self.cbar_fixmin_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')
        self.cbar_fixmax_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')
        self.cbar_fixmin_editbox.textChanged.connect(self.colorbarFixminChanged)
        self.cbar_fixmax_editbox.textChanged.connect(self.colorbarFixmaxChanged)

        self.camera_group = QGroupBox('Camera interaction', parent=self.mainframe)
        self.camera_group.setStyleSheet('QGroupBox { font-weight: bold; font-size: 14px; } ')

        self.hlt_saveframes = QHBoxLayout()
        self.hlt_saveframes.addWidget(self.save_nframes_label)
        self.hlt_saveframes.addWidget(self.save_nframes_spinbox)
        self.hlt_saveframes.addWidget(self.save_nframes_button)

        self.cam_frate_hlt = QHBoxLayout()
        self.cam_frate_hlt.addWidget(self.framerate_label)
        self.cam_frate_hlt.addWidget(self.framerate_spinbox)

        self.exposure_hlt = QHBoxLayout()
        self.exposure_hlt.addWidget(self.exposure_label)
        self.exposure_hlt.addWidget(self.exposure_spinbox)

        #self.cam_gain_hlt = QHBoxLayout()
        #self.cam_gain_hlt.addWidget(self.cam_gain_label)
        #self.cam_gain_hlt.addWidget(self.cam_gain_spinbox)

        self.cam_navgs_hlt = QHBoxLayout()
        self.cam_navgs_hlt.addWidget(self.cam_navgs_label)
        self.cam_navgs_hlt.addWidget(self.cam_navgs_spinbox)

        self.cbar_edit_hlt = QHBoxLayout()
        self.cbar_edit_hlt.addWidget(self.cbar_fixmin_editbox)
        self.cbar_edit_hlt.addWidget(self.cbar_fixmax_editbox)
        self.cbar_vlt = QVBoxLayout()
        self.cbar_vlt.addWidget(self.cbar_fix_label)
        self.cbar_vlt.addLayout(self.cbar_edit_hlt)

        self.autoexp_hlt = QHBoxLayout()
        self.set_autoexposure_button = QPushButton('Auto-adjust exposure')
        self.set_autoexposure_button.clicked.connect(self.set_autoexposure)
        self.show_histogram_button = QPushButton('Show image histogram')
        self.show_histogram_button.clicked.connect(self.show_histogram)
        self.show_histogram_button.setEnabled(False)                      ## disabled the button until I get the function working
        self.autoexp_hlt.addWidget(self.set_autoexposure_button)
        self.autoexp_hlt.addWidget(self.show_histogram_button)

        self.binning_hlt = QHBoxLayout()
        self.binning_label = QLabel('Camera binning:')
        self.binning_spinbox = QSpinBox()
        self.binning_spinbox.setValue(1)
        self.binning_spinbox.setSingleStep(1)
        self.binning_spinbox.setRange(1,8)
        self.binning_spinbox.valueChanged.connect(self.binningChange)
        self.binning_hlt.addWidget(self.binning_label)
        self.binning_hlt.addWidget(self.binning_spinbox)
        self.binning_spinbox.setEnabled(False)                      ## disabled the button until I get the function working

        self.fpp_hlt = QHBoxLayout()
        self.activate_fpp_button = QPushButton('Activate FPP')
        self.activate_fpp_button.clicked.connect(self.initialize_projector)
        self.save_fppdata_button = QPushButton('Save FPP Dataset')
        self.save_fppdata_button.clicked.connect(self.record_fpp_imageset)
        self.save_fppdata_button.setEnabled(False)       ## disabled the button until FPP is activated
        self.fpp_hlt.addWidget(self.activate_fpp_button)
        self.fpp_hlt.addWidget(self.save_fppdata_button)

        self.lctf_hlt = QHBoxLayout()
        self.activate_lctf_button = QPushButton('Activate LCTF')
        self.activate_lctf_button.clicked.connect(self.initialize_lctf)
        self.save_lctfdata_button = QPushButton('Save LCTF Dataset')
        self.save_lctfdata_button.clicked.connect(self.collect_lctf_images)
        self.save_lctfdata_button.setEnabled(False)       ## disabled the button until LCTF is activated
        self.lctf_hlt.addWidget(self.activate_lctf_button)
        self.lctf_hlt.addWidget(self.save_lctfdata_button)

        self.textbox_vlt = QVBoxLayout()
        font = QFont()
        font.setStyleHint(QFont().Monospace)
        font.setFamily('monospace')
        self.outputbox.setFont(font)
        self.textbox_vlt.addWidget(self.outputbox)

        self.vlt1 = QVBoxLayout(self.camera_group)
        self.vlt1.addWidget(self.live_checkbox)
        self.vlt1.addWidget(self.saturation_checkbox)
        self.vlt1.addLayout(self.file_dir_hlt)
        self.vlt1.addLayout(self.file_prefix_hlt)
        self.vlt1.addLayout(self.file_suffix_hlt)
        self.vlt1.addLayout(self.hlt_saveframes)
        self.vlt1.addWidget(self.cam_label)
        self.vlt1.addLayout(self.cam_frate_hlt)
        self.vlt1.addLayout(self.exposure_hlt)
        #self.vlt1.addLayout(self.cam_gain_hlt)
        self.vlt1.addLayout(self.cam_navgs_hlt)
        self.vlt1.addLayout(self.binning_hlt)
        self.vlt1.addLayout(self.cbar_vlt)
        self.vlt1.addLayout(self.autoexp_hlt)
        self.vlt1.addLayout(self.fpp_hlt)
        self.vlt1.addLayout(self.lctf_hlt)
        self.vlt1.addLayout(self.textbox_vlt)

        self.hlt_main = QHBoxLayout(self.mainframe)
        self.hlt_main.addWidget(self.camera_group)
        self.hlt_main.addLayout(self.hlt1)
        return

    ## ===================================
    def createAction(self, text, slot=None, shortcut=None, icon=None, tip=None, checkable=False, signal="triggered"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/{0}.png".format(icon)))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            getattr(action, signal).connect(slot)   ## Qt4: self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

    ## ===================================
    def addActions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
        return

    ## ===================================
    def closeEvent(self, event=None):
        ## Release the camera object.
        if (self.ncameras > 0):
            ## Release reference to camera. We cannot rely on pointer objects being automatically cleaned up 
            ## when going out of scope. The usage of "del" is preferred to assigning the variable to None.
            del self.camera

            # Clear camera list before releasing system
            self.camera_list.Clear()

            # Release system instance
            self.camera_system.ReleaseInstance()

        ## Close the monitor/projector/SLM object.
        if self.has_fpp:
            self.slm.close()

        ## Close the monitor/projector/SLM object.
        if self.has_lctf:
            result = kurios.KuriosClose(self.lctf_hdl)
            if (result != 0):
                print(f'Kurios LCTF failed to close. Error = {result}')

        self.deleteLater()
        return

    ## ===================================
    def liveDataChange(self, state):
        if (state == Qt.Checked) and (self.ncameras > 0):
            QTimer.singleShot(60, self.acquire_new_image)
        else:
            pass

        if (state == Qt.Checked):
            self.exposure_spinbox.setEnabled(True)
            #self.cam_gain_spinbox.setEnabled(True)
        else:
            self.exposure_spinbox.setEnabled(False)
            #self.cam_gain_spinbox.setEnabled(False)

        return

    ## ===================================
    def saturationCheckChange(self, state):
        self.saturated = (self.image >= self.cam_saturation_level)
        self.img_has_saturation = self.saturated.any()

        if (state == Qt.Checked) and self.img_has_saturation:
            self.mycmap = self.satgrey
        else:
            self.mycmap = cm.gray
        return

    ## ===================================
    def initialize_camera(self):
        self.camera_system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        self.camera_list = self.camera_system.GetCameras()
        self.ncameras = self.camera_list.GetSize()
        print(f'Number of cameras detected: {self.ncameras}')

        if (self.ncameras == 0):
            raise ValueError(f'No cameras detected.')

        self.camera = self.camera_list[0]
        self.nodemap_tldevice = self.camera.GetTLDeviceNodeMap()
        self.camera.Init()                              ## Initialize the camera
        self.nodemap = self.camera.GetNodeMap()         ## Retrieve the camera's GenICam nodemap

        if not fsl.set_autoexposure_off(self.nodemap, verbose=False):
            self.outputbox.appendPlainText(f'Failed to turn autoexposure off!')

        if not fsl.set_pixel_format(self.nodemap, 'Mono16', verbose=False):
            self.outputbox.appendPlainText(f'Failed to set the pixel format to Mono16!')

        if not fsl.set_binning(self.nodemap, self.binning, verbose=False):
            self.outputbox.appendPlainText(f'Failed to set the pixel binning to 1!')

        ## Ask the camera what the allowed minimum and maximum image dimensions are.
        img_minmax = fsl.get_image_minmax(self.nodemap, verbose=False)
        self.image_minwidth = img_minmax[0]
        self.image_maxwidth = img_minmax[1]
        self.image_minheight = img_minmax[2]
        self.image_maxheight = img_minmax[3]
        if (sum(array(img_minmax)) == 0):
            self.outputbox.appendPlainText(f'Failed to read the allowed image sizes from the camera!')
        
        fsl.set_autogain_off(self.nodemap, verbose=False)
        fsl.set_exposure_time(self.nodemap, self.exposure, verbose=False)
        self.framerate = fsl.get_framerate(self.nodemap, verbose=False)

        (self.min_exposure,self.max_exposure) = fsl.get_exposure_minmax(self.nodemap, verbose=False)
        if ((self.min_exposure + self.max_exposure) == 0.0):
            self.outputbox.appendPlainText(f'Failed to read the allowed exposure range!')

        (self.Ny,self.Nx) = fsl.get_image_width_height(self.nodemap, verbose=False)
        
        return

    ## ===================================
    def initialize_image_data(self):
        self.image = self.capture_image(1, verbose=True)
        if self.image is None:
            raise ValueError(f'Failed to collect an image from the camera!')

        self.image_counter += 1

        ## Update the saturation flags.
        if self.saturation_checkbox.isChecked():
            self.saturated = (self.image >= self.cam_saturation_level)
            self.img_has_saturation = self.saturated.any()

            if self.img_has_saturation:
                self.mycmap = self.satgrey
            else:
                self.mycmap = cm.gray
        else:
            self.mycmap = cm.gray

        ## Now we need to initialize the Matplotlib display, to get a reference to the display object.
        mpl1 = self.mplwidget.canvas
        vmin = self.image_vmin_str
        vmax = self.image_vmax_str
        if (vmin == 'Min'): vmin = amin(self.image)
        if (vmax == 'Max'): vmax = amax(self.image)
        if (vmin != None) and (vmax != None) and (vmax < vmin):
            vmax = None

        self.img_obj = mpl1.ax.imshow(self.image, vmin=vmin, vmax=vmax, cmap=self.mycmap)
        self.cb = mpl1.fig.colorbar(self.img_obj, shrink=0.85, pad=0.025)
        self.first_draw = False
        mpl1.draw()

        return

    ## ===================================
    def acquire_new_image(self):
        if (self.ncameras > 0):
            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            self.image_counter += 1
            self.statusbar_label.setText(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')

            ## Update the saturation flags.
            if self.saturation_checkbox.isChecked():
                self.saturated = (self.image >= self.cam_saturation_level)
                self.img_has_saturation = self.saturated.any()
                #print(f'self.img_has_saturation = {self.img_has_saturation}, amax(self.image) = {amax(self.image)}, self.cam_saturation_level = {self.cam_saturation_level}')

        self.draw_fig1()

        if self.live_checkbox.isChecked() and (self.ncameras > 0):
            ## Emit a signal to repeat this action in another 50ms.
            QTimer.singleShot(10, self.acquire_new_image)

        return

    ## ===================================
    def frameRateChange(self):
#        if (self.ncameras == 0) or (self.framerate_spinbox.value() == 0):
#            return
#
#        self.framerate = self.framerate_spinbox.value()
#        current_cam_framerate = self.camera.camera_nodes.AcquisitionFrameRate.get_node_value()     ## rotpy style
#        if (self.framerate == current_cam_framerate):
#            return
#        else:
#            self.camera.camera_nodes.AcquisitionFrameRate.set_node_value(self.framerate)
#
#        exposure_limit = 1000000.0 / self.framerate
#        if (self.exposure > exposure_limit):
#            self.exposure = exposure_limit
#            print(f'BEFORE: self.nints_spinbox=[{self.exposure_spinbox.value()}]')
#            self.exposure_spinbox.setValue(exposure_limit)
#            print(f'AFTER: self.nints_spinbox=[{self.exposure_spinbox.value()}]')
#            self.camera.camera_nodes.AcquisitionFrameRate.set_node_value(self.framerate)
#        elif (exposure_limit > self.max_exposure):
#            self.exposure_spinbox.setRange(self.min_exposure, exposure_limit)
#        else:
#            self.exposure_spinbox.setRange(self.min_exposure, self.max_exposure)
#
#        print(f'self.framerate={self.framerate}, self.exposure={self.exposure}, self.max_exposure={self.max_exposure}')

        return

    ## ===================================
    def exposureChange(self):
        ## Disable this function when LIVE checkbox is on.
        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            new_exposure = self.exposure_spinbox.value()
            if (new_exposure > self.max_exposure):
                new_exposure = self.max_exposure
            if (new_exposure < self.min_exposure):
                new_exposure = self.min_exposure
            
            self.exposure = new_exposure
            self.exposure_spinbox.setValue(new_exposure)
            #new_exposure_in_usec = new_exposure * 1000
            fsl.set_exposure_time(self.nodemap, new_exposure)
            self.outputbox.appendPlainText(f'Setting exposure = {self.exposure} usec')
        return

    ## ===================================
    def gainChange(self):
#        ## Disable this function when LIVE checkbox is on.
#        if (self.ncameras > 0) and self.live_checkbox.isChecked():
#            self.cam_gain = self.cam_gain_spinbox.value()
#            self.camera.camera_nodes.Gain.set_node_value(self.cam_gain)    ## from rotpy
        return

    ## ===================================
    def navgsChange(self, state):
        self.navgs = self.cam_navgs_spinbox.value()
        self.outputbox.appendPlainText(f'Setting navgs = {self.navgs}')
        return

    ## ===================================
    def colorbarFixminChanged(self, mintext):
        mpl1 = self.mplwidget.canvas
        maxtext = self.cbar_fixmax_editbox.text()
        ## If the textbox string is "Min" then we should set vmin=None in order to let it be set by Matplotlib automatically.
        ## If the textbox is not a valid number, then show the text in grey.
        if (mintext.lower() == 'min'):
            vmin = None
            self.cbar_fixmin_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')
        else:
            ## Take the values here and send them to the current image window's colorbar.
            if is_number(mintext):
                vmin = float32(mintext)
                self.cbar_fixmin_editbox.setStyleSheet('color: rgba(0, 0, 0, 1);')
            else:
                ## The string is not valid, so just allow the range to be set automatically.
                vmin = None
                self.cbar_fixmin_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')

        if (maxtext.lower() == 'max'):
            vmax = None
        else:
            ## Take the values here and send them to the current image window's colorbar.
            if is_number(maxtext):
                vmax = float32(maxtext)
            else:
                ## The string is not valid, so just allow the range to be set automatically.
                vmax = None

        self.image_vmin_str = vmin
        self.image_vmax_str = vmax
        self.outputbox.appendPlainText(f'vmin = {vmin}, vmax = {vmax}')

        ## Finally, update the colorbar.
        self.cb.mappable.set_clim(vmin=vmin, vmax=vmax)
        self.cb.draw_all()      ## this is deprecated. When the bugs are worked out, replace it with the commented line below
        #mpl1.fig.draw_without_rendering()

        return

    ## ===================================
    def colorbarFixmaxChanged(self, maxtext):
        mpl1 = self.mplwidget.canvas
        mintext = self.cbar_fixmin_editbox.text()
        if (mintext.lower() == 'min'):
            vmin = None
        else:
            ## Take the values here and send them to the current image window's colorbar.
            if is_number(mintext):
                vmin = uint16(mintext)
            else:
                ## The string is not valid, so just allow the range to be set automatically.
                vmin = None

        ## If the textbox string is "Max" then we should set vmax=None in order to let it be set by Matplotlib automatically.
        ## If the textbox is not a valid number, then show the text in grey.
        if (maxtext.lower() == 'max'):
            vmax = None
            self.cbar_fixmax_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')
        else:
            ## Take the values here and send them to the current image window's colorbar.
            if is_number(maxtext):
                vmax = uint16(maxtext)
                self.cbar_fixmax_editbox.setStyleSheet('color: rgba(0, 0, 0, 1);')
            else:
                ## The string is not valid, so just allow the range to be set automatically.
                vmax = None
                self.cbar_fixmax_editbox.setStyleSheet('color: rgba(125, 125, 125, 1);')

        self.image_vmin_str = vmin
        self.image_vmax_str = vmax
        self.outputbox.appendPlainText(f'vmin = {vmin}, vmax = {vmax}')

        ## Finally, update the colorbar.
        self.cb.mappable.set_clim(vmin=vmin, vmax=vmax)
        self.cb.draw_all()      ## this is deprecated. When the bugs are worked out, replace it with the commented line below
        #mpl1.fig.draw_without_rendering()

        return

    ## ===================================
    def draw_fig1(self):
        mpl1 = self.mplwidget.canvas
        vmin = self.image_vmin_str
        vmax = self.image_vmax_str
        if (vmin == 'Min'): vmin = amin(self.image)
        if (vmax == 'Max'): vmax = amax(self.image)
        if (vmin != None) and (vmax != None) and (vmax < vmin):
            vmax = None

        ## Update the saturation flags.
        if self.saturation_checkbox.isChecked() and self.img_has_saturation:
            self.mycmap = self.satgrey
            #self.mycmap = cm.viridis
        else:
            self.mycmap = cm.gray

        self.img_obj.set_data(self.image)
        self.img_obj.set_cmap(self.mycmap)       ## update the colormap in case there is a change in saturation state

        ## Update the colorbar to the new limits.
        self.cb.mappable.set_clim(vmin=vmin, vmax=vmax)
        mpl1.draw()

        return

    ## ===================================
    def fileOpen(self):
        (filename, ok) = QFileDialog.getOpenFileName(self, 'Load an image', '', 'Images (*.png *.jpg *.tif *.tiff *.npz)')
        if not filename:
            return

        suffix = os.path.splitext(filename)[1]

        if (suffix == 'npz'):
            self.image = load(filename)['image']
        else:
            import_image = imread(filename)
            if (ndim(import_image) == 3):
                self.image = float32(import_image[:,:,0]) + float32(import_image[:,:,0]) + float32(import_image[:,:,0])[::-1,:]
            elif (ndim(import_image) != 2):
                raise ImportError('Image format does not seem to be compatible.')
            else:
                self.image = import_image[::-1,:]

            self.draw_fig1()

        return

    ## ===================================
    def fileSave(self, filename=''):
        if not filename:
            (filename,ok) = QFileDialog.getSaveFileName(self, "Save image to a file", '000000.tif')
            if not filename:
                return

        suffix = os.path.splitext(filename)[1][1:]
        self.outputbox.appendPlainText(f'Saving "{filename}"')
        if suffix in ('jpg','png'):
            img8bit = uint8(self.image[::-1,:] * 255.0 / amax(self.image))
            imsave(filename, img8bit)
        elif suffix in ('tif','tiff'):
            imsave(filename, self.image[::-1,:])
        elif suffix == 'npz':
            savez(filename, image=self.image)

        self.file_counter += 1

        return

    ## ===================================
    def capture_image(self, nframes=1, verbose=False):
        if not hasattr(self, 'camera'):
            return(None)
        
        if (nframes == 1):
            if (self.navgs == 1):
                (self.image, self.ts) = fsl.acquire_one_image(self.camera, self.nodemap)
                if self.image is None:
                    return(None)
                self.image = self.image // 16   ## Divide by 16 to remove the 4 extra bits going from 16-bit to 12-bit data
            elif (self.navgs > 1):
                (img_set, ts_set) = fsl.acquire_num_images(self.camera, self.nodemap, self.navgs)
                if img_set is None:
                    return(None)
                self.image = uint32(mean(img_set, axis=2)) // 16   ## Divide by 16 to remove the 4 extra bits going from 16-bit to 12-bit data
                self.outputbox.appendPlainText(f'img_set.shape={img_set.shape}, amax(image)={amax(self.image):.0f}')
                print(f'amin(img_set[:,:,0])={amin(img_set[:,:,0]):.1f}, amax(img_set[:,:,0])={amax(img_set[:,:,0]):.1f}, amin(img_set[:,:,1])={amin(img_set[:,:,1]):.1f}, amax(img_set[:,:,1])={amax(img_set[:,:,1]):.1f}')
                self.ts = ts_set[0]
            return(self.image)
        elif (nframes > 1):
            if (self.navgs == 1):
                video = zeros((self.Nx,self.Ny,nframes), 'uint16')
                for n in range(nframes):
                    (self.image, self.ts) = fsl.acquire_one_image(self.camera, self.nodemap)
                    if self.image is None:
                        return(None)
                    video[:,:,n] = self.image // 16   ## Divide by 16 to remove the 4 extra bits going from 16-bit to 12-bit data
            elif (self.navgs > 1):
                ## Save N frames and average them together to each one frame of the video.
                video = zeros((self.Nx,self.Ny,nframes), 'uint16')

                for n in range(nframes):
                    (img_set, ts_set) = fsl.acquire_num_images(self.camera, self.nodemap, self.navgs)
                    if img_set is None:
                        return(None)
                    self.image = uint32(mean(img_set, axis=2)) // 16   ## Divide by 16 to remove the 4 extra bits going from 16-bit to 12-bit data
                    self.ts = ts_set[0]
                    video[:,:,n] = self.image / 16   ## Divide by 16 to remove the 4 extra bits going from 16-bit to 12-bit data

            return(video)
        else:
            raise ValueError('How did we get here?')
        
        return(None)

    ## ===================================
    def save_video_sequence(self):
        nframes = self.save_nframes_spinbox.value()

        file_dir = self.file_dir_editbox.text()
        if not file_dir:
            file_dir = self.cwd
        elif (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_dir = file_dir.replace('\\', '/')
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        if (nframes == 1):
            ## Note: the "file_counter" is what we use to keep track of all images saved so far in this session, so that we don't
            ## overwrite previous files. The "fileSave()" function keep track of incrementing this value each time it is called.
            filename = f'{file_dir}{file_prefix}_{self.file_counter:04}.{file_suffix}'
            self.fileSave(filename)
        elif (nframes > 1):
            ## First turn off the live stream capture. Turn it back on when done.
            initial_state_is_live = self.live_checkbox.isChecked()
            if initial_state_is_live:
                self.live_checkbox.setChecked(False)
            video = self.capture_image(nframes)
            if video is None:
                self.outputbox.appendPlainText(f'Failed to collect video!')
                return

            if (file_suffix == 'npz'):
                vid_filename = file_dir + 'video.npz'
                savez(vid_filename, video=video)
                self.outputbox.appendPlainText(f'Saved video to {vid_filename}')
            else:
                ## Note: the "file_counter" is what we use to keep track of all images saved so far in this session, so that we don't
                ## overwrite previous files. The "fileSave()" function keep track of incrementing this value each time it is called.
                nframes = video.shape[2]
                for n in range(nframes):
                    filename = f'{file_dir}{file_prefix}_{self.file_counter:04}.{file_suffix}'
                    self.fileSave(filename)

            if initial_state_is_live:
                self.live_checkbox.setChecked(True)

        return

    ## ===================================
    def set_autoexposure(self):
        ## Now, send the camera commands to turn on the autoexposure, then turn it back off...
        fsl.set_autoexposure_on(self.nodemap)
        time.sleep(1.0)             ## wait for 1sec for the autoexposure to settle
        fsl.set_autoexposure_off(self.nodemap)
        self.exposure = fsl.get_exposure(self.nodemap, verbose=False)
        self.exposure_spinbox.setValue(self.exposure)
        return

    ## ===================================
    def binningChange(self):
        if (self.ncameras == 0):
            return

        temporary = self.binning        ## store the current value in case there is an error in the new setting
        if not fsl.set_binning(self.nodemap, self.binning_spinbox.value()):
            self.outputbox.appendPlainText(f'Failed to set the binning value!')
            return

        self.binning = self.binning_spinbox.value()
        self.outputbox.appendPlainText(f'Setting binning = {self.binning}')
        
        ## Now that the binning has changed, modify the image size, and update the statusbar string.
        (self.Ny,self.Nx) = fsl.get_image_width_height(self.nodemap, verbose=False)
        self.statusbar_label.setText(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')

        return

    ## ===================================
    def initialize_projector(self):
        if self.has_fpp:
            return
            
        import slmpy

        try:
            ## Create the object that handles the SLM array.
            ## By default, "slmpy" uses the second display (i.e. monitor=1) for displaying images. If you have more
            ## than one monitor/projector/SLM, you may want to specify which monitor is the monitor/projector/SLM.
            ## The "isImageLock=True" variable means that the program will wait until the new image display is completed
            ## before continuing to the next step in the code (in case you are operating in a fast loop).
            self.slm = slmpy.SLMdisplay(monitor=1, isImageLock=True)
        except ValueError as err:
            self.outputbox.appendPlainText(f'Error: {err}')
            return

        ## Ask for the pixel dimensions of the monitor/projector/SLM display.
        (self.resY,self.resX) = self.slm.getSize()
        self.outputbox.appendPlainText(f'Projecting an ({self.resX},{self.resY}) image.')

        ## Make a set of coordinates for generating the fringe patterns for projection.
        (self.proj_xcoord,self.proj_ycoord) = indices((self.resX,self.resY))

        self.project_next_image()
        self.has_fpp = True
        self.save_fppdata_button.setEnabled(True)

        return

    ## ===================================
    def project_next_image(self):
        ## If the current phase is equal to "nphases" then this is the same thing as setting it to zero.
        if (self.phasenum >= self.nphases):
            self.phasenum = 0

        k = 2.0 * pi * self.nfringes / self.resY
        phi_shift = 2.0 * pi * self.phasenum / self.nphases

        ## Generate the sinusoidal fringe pattern. Note that this has to be uint8.
        self.proj_img = uint8(rint(255.0*(0.5 + 0.5*cos(k*self.proj_ycoord + phi_shift))))

        ## Send this image to the monirot/projector/SLM.
        self.slm.updateArray(self.proj_img)

        return

    ## ===================================
    def record_fpp_imageset(self):
        file_dir = self.file_dir_editbox.text()
        if file_dir and (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        for shiftnum in range(self.nphases):
            self.phasenum = shiftnum
            phasevalue_deg = int(rint(360.0 * self.phasenum / self.nphases))
            self.project_next_image()
            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            filename = f'{file_dir}{file_prefix}_{phasevalue_deg:03}.{file_suffix}'
            self.fileSave(filename)

        return

    ## ===================================
    def initialize_lctf(self):
        import kurios

        devs = kurios.KuriosListDevices()
        if (len(devs) <= 0):
            self.outputbox.appendPlainText(f'No LCTF device was detected. Aborting...')
            return

        ## Initialize the handle to Kurios' common functions, then set the main parameters of the system.
        Kurios = devs[0]
        self.lctf_hdl = kurios.CommonFunc(Kurios[0])
        kurios.SetMainParameters(self.lctf_hdl)   # once you understand the interface, you won't need this command
        result = kurios.KuriosSetOutputMode(self.lctf_hdl, 2) ## 1 = manual; 2 = sequenced(internal clock triggered) ; 3 = sequenced(external triggered); 4 = analog signal controlled(  internal clock triggered); 5 = analog signal controlled(external triggered)

        self.minwave = [0]  ## the minimum wavelength in nm allowed by this LCTF system
        self.maxwave = [0]  ## the maximum wavelength in nm allowed by this LCTF system
        result = kurios.KuriosGetSpecification(self.lctf_hdl, self.maxwave, self.minwave)

        if (self.lctf_currentwave >= self.minwave) and (self.lctf_currentwave <= self.maxwave):
            result = kurios.KuriosSetWavelength(self.lctf_hdl, self.lctf_currentwave) ## the range of wavelength is between MinWavelength and MaxWavelength

        self.has_lctf = True

        return

    ## ===================================
    def set_next_lctf_wave(self):
        self.lctf_wave_counter += 1
        if (self.lctf_currentwave >= self.minwave) and (self.lctf_currentwave <= self.maxwave):
            self.lctf_currentwave = self.wavelist[self.lctf_wave_counter]
        else:
            self.outputbox.appendPlainText(f'Failed to set the LCTF wavelength to {self.lctf_currentwave}nm.')
            self.lctf_wave_counter = 0
            self.lctf_currentwave = self.wavelist[self.lctf_wave_counter]
        return

    ## ===================================
    def collect_lctf_images(self):
        file_dir = self.file_dir_editbox.text()
        if file_dir and (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        for w in range(len(self.wavelist)):
            self.set_next_lctf_wave(w)
            wavevalue_nm = self.lctf_currentwave
            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            filename = f'{file_dir}{file_prefix}_{wavevalue_nm:03}.{file_suffix}'
            self.fileSave(filename)

        return

    ## ===================================
    def show_histogram(self):
        self.outputbox.appendPlainText(f'Histogram function is not yet implemented')
        return

## ======================================================================================================
def is_even(x):
    return(x % 2 == 0)

## ======================================================================================================
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

## ======================================================================================================
## ======================================================================================================

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName('Interactive Full-Stokes Video Camera')

    ## Calculate the current desktop screen size available. Store the results as global variables.
    screenSizeObject = QDesktopWidget().screenGeometry(-1)
    screen_height = screenSizeObject.height()
    screen_width = screenSizeObject.width()
    gui_height = screen_height - 100
    gui_width = screen_width - 100
    #print("Screen size (width,height): ("  + str(screen_width) + ","  + str(screen_height) + ")")
    #print("GUI positions (width,height): (100,100,"  + str(gui_height) + ","  + str(gui_height) + ")")

    mw = MainWindow()
    mw.setWindowTitle('Interactive Full-Stokes Video Camera')
    mw.show()
    mw.acquire_new_image()
    sys.exit(app.exec_())       ## start the execution loop
