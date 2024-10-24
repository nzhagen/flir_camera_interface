## TODO:
## 1. When the "Live Data" button is OFF, enable a pushbutton that shows a popup Histogram of the current image.
##    It would really help to be able to zoom this histogram to check values.
## 2. If you want to be able to set the FrameRate manually, you will first have to set the "FrameRateAuto" to "Off".
## 3. Allow a user to save filenames using the timestamps instead of the file_counter.
## 4. Consider capturing error messages and sending them into the outputbox. The relevant code would look like:
##        except Exception as err_msg:
##            self.outputbox.appendPlainText(err_msg)
## 5. Make another version of the interface based on two cameras operating simultaneously. Nice for UV-VIS or VIS-NIR dual camera use.

from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence, QIcon, QColor, QFont, QImage, QPixmap, QPainter
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QMainWindow, QSizePolicy, QWidget, QVBoxLayout, QMenuBar, QStatusBar,
                             QHBoxLayout, QAction, QDialog, QFrame, QFileDialog, QGroupBox, QRadioButton, QGridLayout,
                             QTabWidget, QLabel, QCheckBox, QSpinBox, QPlainTextEdit, QMessageBox, QErrorMessage,
                             QDoubleSpinBox, QDialogButtonBox, QLineEdit, QLabel, QPushButton, QFormLayout)

## import the Qt5Agg figure canvas object, that binds figures to the Qt5Agg backend. It also inherits from QWidget.
import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid1 import ImageGrid, make_axes_locatable
import matplotlib as mpl
mpl.rcParams['image.origin'] = 'lower'  ## set the lower left corner to be the (0,0) position for the image
mpl.rcParams['image.cmap'] = 'gray'

import numpy
from numpy import (pi, array, asarray, linspace, indices, amin, amax, sqrt, exp, mean, std, nan, NaN,
                   logical_and, zeros, uint8, mgrid, ones, uint32, load, float32, where, arange, uint16,
                   logical_or, log, savez, empty, reshape, ndim, cos, rint, log2, sort, unique)
numpy.seterr(all='raise')
numpy.seterr(invalid='ignore')

import struct, time, os, sys
from glob import glob
try:
    from imageio.v2 import imread, imsave
except:
    from imageio import imread, imsave

try:
    import PySpin
    import flir_spin_library as fsl
except:
    msg = 'Cannot find the PySpin library. Did you maybe forget to activate the "flir" environment?'
    print(msg)
    raise ValueError(msg)

this_folder = os.path.dirname(os.path.realpath(__file__))
print('this_folder=', this_folder)
sys.path.append(this_folder + '/devices/')

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
class CustomDialog(QDialog):
    def __init__(self, image):
        super().__init__()
        self.image = image[::-1,:]

        #self.setWindowTitle("HELLO!")
        #QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        #self.buttonBox = QDialogButtonBox(QBtn)
        #self.buttonBox.accepted.connect(self.accept)
        #self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        #message = QLabel("Something happened, is that OK?")
        #self.layout.addWidget(message)
        #self.layout.addWidget(self.buttonBox)

        self.mplwidget = MPLWidget()
        self.layout.addWidget(self.mplwidget)

        mpl1 = self.mplwidget.canvas
        self.img_obj = mpl1.ax.imshow(self.image)
        self.cb = mpl1.fig.colorbar(self.img_obj, shrink=0.85, pad=0.025)
        mpl1.ax.axis('off')
        mpl1.draw()

        self.setLayout(self.layout)

## ===========================================================================================================
class MainWindow(QMainWindow):
    def __init__(self, gui_height=None, gui_width=None, parent=None):
        super(MainWindow, self).__init__(parent)
        #self.showMaximized()
        self.gui_height = gui_height
        self.gui_width = gui_width

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
        self.cropping = 0
        self.cam_bitdepth = 12 + uint16(log2(self.binning**2))      ## camera bit depth
        self.cam_saturation_level = (2**self.cam_bitdepth) - 1 - 7  ## why do we need '-7' here?!
        self.img_has_saturation = False
        self.outputbox = None       ## need to define this variable early to prevent error -- it gets redefined later
        self.cwd = os.getcwd()
        self.timer_delay = 50       ## time in ms to delay before requesting a new image from the camera
        self.autoscale_brightness = True        ## whether to automatically scale the display so the darkest pixel is black and the brightest is white
        self.ncameras = 0           ## Number of cameras connected here (normally 0 or 1)
        self.has_fpp = False        ## Is a projector activated for fringe projection profilometry (FPP)?
        self.has_lctf = False       ## Is a liquid-crystal tunable filter (LCTF) activated?
        self.has_motor = False      ## Is the Thorlabs rotational motor activated?

        if (self.binning > 1):
            print(f'Binning is set to {self.binning}...')

        ## Whether to use tone-mapping when converting from 12-bit to 8-bit for display. If tone_mapping_scale is 16 then use bit truncation rather than tone-mapping.
        self.tone_mapping_scale = uint16(pow(2.0, self.cam_bitdepth - 8))
        #self.tone_mapping_scale = 16
        self.img8bit = None         ## the 8-bit (tone-mapped) version of the raw image

        ## Define the image scale for each image -- we will need these for the manual controls on the colorbars of each image.
        self.image_vmin_str = 'Min'
        self.image_vmax_str = 'Max'

        ## Set the window background to a medium gray color.
        self.grey_palette = self.palette()
        self.grey_palette.setColor(self.backgroundRole(), QColor(225,225,225))
        self.setPalette(self.grey_palette)

        fileOpenAction = self.createAction("&Open File", self.fileOpen, QKeySequence.Open, "fileopen", "Load an image")
        fileSaveAction = self.createAction("&Save Image", self.fileSave, QKeySequence.Save, "filesave", "Save an image")
        #videoSaveAction = self.createAction("Save &Video Sequence", self.save_video_sequence, QKeySequence.Paste, "videosave", "Save a video sequence")
        fileQuitAction = self.createAction("&Quit", self.close, "Ctrl+Q", "quit", "Close the application")

        self.mb = self.menuBar()
        self.mb.setObjectName('menubar')
        self.fileMenu = self.mb.addMenu('&File')
        self.addActions(self.fileMenu, (fileOpenAction, fileSaveAction, fileQuitAction))

        self.mainframe = QFrame(self)
        self.setCentralWidget(self.mainframe)

        self.saturation_checkbox = QCheckBox('Paint saturated pixels red', self)
        self.saturation_checkbox.setChecked(True)
        self.saturation_checkbox.stateChanged.connect(self.saturationCheckChange)

        ## This "autoscale_brightness" is linked to the tone mapping of the display. But I can't remember what I was doing with this.
        #self.autoscale_checkbox = QCheckBox('Autoscale display brightness', self)
        #self.autoscale_checkbox.setChecked(self.autoscale_brightness)
        #self.autoscale_checkbox.stateChanged.connect(self.autoscaleChange)

        ## The outputbox object needs to go before camera initialization, so that any messages have a place to get printed.
        self.outputbox = QPlainTextEdit('')
        self.outputbox.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.statusbar = QStatusBar()
        self.statusbar.showMessage('')

        self.live_checkbox = QCheckBox('Live Data', self)
        self.live_checkbox.setChecked(True)         ## temporarily set to true until we find out whether a camera is connected

        ## Initialize the camera and grab the first image.
        self.image_widget = QLabel()
        self.image_widget.mousePressEvent = self.image_clicked
        self.initialize_camera()

        if (self.ncameras > 0):
            self.image = self.capture_image(1, verbose=True)
        else:
            self.image = imread('default_image.tif')[::-1,:]
            self.framerate = 0
            self.min_exposure = 1
            self.max_exposure = 1000000
            #(self.Ny,self.Nx) = self.image.shape

        ## The QHBoxLayout for the image is needed to ensure that the image display will automatically stretch with the window geometry.
        self.vlt1 = QVBoxLayout()
        self.vlt1.addWidget(self.image_widget)
        self.vlt1.addWidget(self.statusbar)

        self.file_dir_label = QLabel('File directory:')
        self.file_prefix_label = QLabel('File prefix:')
        self.file_suffix_label = QLabel('File suffix:')
        self.file_dir_editbox = QLineEdit('')
        self.file_prefix_editbox = QLineEdit('image')
        self.file_suffix_editbox = QLineEdit('tif')
        self.file_dir_editbox.textChanged.connect(self.saveDirChanged)
        self.file_prefix_editbox.textChanged.connect(self.savePrefixChanged)
        self.file_suffix_editbox.textChanged.connect(self.saveSuffixChanged)

        self.save_nframes_label = QLabel('# video frames: ')
        self.save_nframes_spinbox = QSpinBox()
        self.save_nframes_spinbox.setRange(1,99999)
        self.save_nframes_spinbox.setValue(1)
        self.save_nframes_spinbox.setSingleStep(1)
        self.save_nframes_button = QPushButton('Save Frame(s)')
        self.save_nframes_button.clicked.connect(self.save_video_sequence)
        #self.save_nframes_button.clicked.connect(self.fastsave_video)

        self.convert_video_button = QPushButton('Convert all frames in dir to video')
        self.convert_video_button.clicked.connect(self.convert_frames_to_movie)

        self.file_dir_hlt = QHBoxLayout()
        self.file_dir_hlt.addWidget(self.file_dir_label)
        self.file_dir_hlt.addWidget(self.file_dir_editbox)
        self.file_dir_hlt.addWidget(self.save_nframes_label)
        self.file_dir_hlt.addWidget(self.save_nframes_spinbox)

        self.file_prefix_hlt = QHBoxLayout()
        self.file_prefix_hlt.addWidget(self.file_prefix_label)
        self.file_prefix_hlt.addWidget(self.file_prefix_editbox)
        self.file_prefix_hlt.addWidget(self.file_suffix_label)
        self.file_prefix_hlt.addWidget(self.file_suffix_editbox)

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
            self.framerate_label.setStyleSheet('color: rgba(125, 125, 125, 1);')

        ## Disable the framerate stuff for now.
        self.framerate_spinbox.setEnabled(False)

        self.exposure_label = QLabel('Exposure time (\u03bcs)')
        self.exposure_spinbox = QSpinBox()
        self.exposure_spinbox.setSingleStep(1000)
        self.exposure_label.setStyleSheet('color: rgba(125, 125, 125, 1);')
        self.exposure_spinbox.setRange(1,1000000)       ## temporary values until we know the range of the camera
        self.exposure_spinbox.setValue(self.exposure)   ## note that the setValue() function has to come last in this block!
        self.exposure_spinbox.valueChanged.connect(self.exposureChange)
        self.exposure_spinbox.setEnabled(False)

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

        self.update_image_params()

        self.camera_group = QGroupBox('Camera interaction', parent=self.mainframe)
        self.camera_group.setStyleSheet('QGroupBox { font-weight: bold; font-size: 14px; } ')

        self.hlt_saveframes = QHBoxLayout()
        self.hlt_saveframes.addWidget(self.save_nframes_button)
        self.hlt_saveframes.addWidget(self.convert_video_button)

        self.cam_frate_hlt = QHBoxLayout()
        self.cam_frate_hlt.addWidget(self.framerate_label)
        self.cam_frate_hlt.addWidget(self.framerate_spinbox)

        self.exposure_hlt = QHBoxLayout()
        self.exposure_hlt.addWidget(self.exposure_label)
        self.exposure_hlt.addWidget(self.exposure_spinbox)

        self.cam_navgs_hlt = QHBoxLayout()
        self.cam_navgs_hlt.addWidget(self.cam_navgs_label)
        self.cam_navgs_hlt.addWidget(self.cam_navgs_spinbox)

        self.autoexp_hlt = QHBoxLayout()
        self.do_autoexposure_button = QPushButton('Auto-adjust exposure')
        self.do_autoexposure_button.clicked.connect(self.do_autoexposure)
        if (self.ncameras == 0) or not self.live_checkbox.isChecked():
            self.do_autoexposure_button.setEnabled(False)                      ## disabled the button until I get the function working

        self.show_histogram_button = QPushButton('Show image histogram')
        self.show_histogram_button.clicked.connect(self.show_histogram)
        self.show_histogram_button.setEnabled(False)                      ## disabled the button until I get the function working
        self.autoexp_hlt.addWidget(self.do_autoexposure_button)
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

        self.cropping_hlt = QHBoxLayout()
        self.cropping_label = QLabel('Camera cropping:')
        self.cropping_spinbox = QSpinBox()
        self.cropping_spinbox.setValue(0)
        self.cropping_spinbox.setSingleStep(1)
        self.cropping_spinbox.setRange(0,3)
        self.cropping_spinbox.valueChanged.connect(self.croppingChange)
        #self.cropping_hlt.addWidget(self.cropping_label)
        #self.cropping_hlt.addWidget(self.cropping_spinbox)         ## disabled until I get the function working

        self.fpp_hlt = QHBoxLayout()
        self.activate_fpp_button = QPushButton('Activate FPP')
        self.activate_fpp_button.clicked.connect(self.activate_projector)
        self.save_fppdata_button = QPushButton('Save FPP Dataset')
        self.save_fppdata_button.clicked.connect(self.collect_fpp_imageset)
        self.save_fppdata_button.setEnabled(False)       ## disabled the button until FPP is activated
        self.fpp_hlt.addWidget(self.activate_fpp_button)
        self.fpp_hlt.addWidget(self.save_fppdata_button)

        self.lctf_hlt = QHBoxLayout()
        self.activate_lctf_button = QPushButton('Activate LCTF')
        self.activate_lctf_button.clicked.connect(self.activate_lctf)
        self.save_lctfdata_button = QPushButton('Save LCTF Dataset')
        self.save_lctfdata_button.clicked.connect(self.collect_lctf_imageset)
        self.save_lctfdata_button.setEnabled(False)       ## disabled the button until LCTF is activated
        self.lctf_hlt.addWidget(self.activate_lctf_button)
        self.lctf_hlt.addWidget(self.save_lctfdata_button)

        self.motor_hlt = QHBoxLayout()
        self.activate_motor_button = QPushButton('Activate Motor')
        self.activate_motor_button.clicked.connect(self.activate_motor)
        self.save_hurlbut_data_button = QPushButton('Save Hurlbut Filter Dataset')
        self.save_hurlbut_data_button.clicked.connect(self.collect_hurlbut_filter_imageset)
        self.save_hurlbut_data_button.setEnabled(False)       ## disabled the button until LCTF is activated
        self.motor_hlt.addWidget(self.activate_motor_button)
        self.motor_hlt.addWidget(self.save_hurlbut_data_button)

        self.textbox_vlt = QVBoxLayout()
        font = QFont()
        font.setStyleHint(QFont().Monospace)
        font.setFamily('monospace')
        self.outputbox.setFont(font)
        self.textbox_vlt.addWidget(self.outputbox)

        self.vlt2 = QVBoxLayout(self.camera_group)
        self.vlt2.addWidget(self.live_checkbox)
        self.vlt2.addWidget(self.saturation_checkbox)
        #self.vlt2.addWidget(self.autoscale_checkbox)
        self.vlt2.addLayout(self.file_dir_hlt)
        self.vlt2.addLayout(self.file_prefix_hlt)
        self.vlt2.addLayout(self.hlt_saveframes)
        self.vlt2.addWidget(self.cam_label)
        self.vlt2.addLayout(self.cam_frate_hlt)
        self.vlt2.addLayout(self.exposure_hlt)
        self.vlt2.addLayout(self.cam_navgs_hlt)
        self.vlt2.addLayout(self.binning_hlt)
        self.vlt2.addLayout(self.cropping_hlt)
        self.vlt2.addLayout(self.autoexp_hlt)
        self.vlt2.addLayout(self.fpp_hlt)
        self.vlt2.addLayout(self.lctf_hlt)
        self.vlt2.addLayout(self.motor_hlt)
        self.vlt2.addLayout(self.textbox_vlt)

        self.hlt_main = QHBoxLayout(self.mainframe)
        self.hlt_main.addWidget(self.camera_group)
        self.hlt_main.addLayout(self.vlt1)

        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            self.exposure_spinbox.setEnabled(True)
            self.exposure_spinbox.setRange(uint32(self.min_exposure),uint32(self.max_exposure))
            self.outputbox.appendPlainText(f'Allowed exposure time min={self.min_exposure:.0f}, max={self.max_exposure:.0f}')

        if (self.ncameras > 0):
            self.live_checkbox.setChecked(self.ncameras > 0)
        else:
            self.live_checkbox.setEnabled(False)
        self.live_checkbox.stateChanged.connect(self.liveDataChange)

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
            self.lctf_device_handle.close()

        self.deleteLater()
        return

    ## ===================================
    def liveDataChange(self, state):
        if (state == Qt.Checked) and (self.ncameras > 0):
            QTimer.singleShot(self.timer_delay, self.acquire_new_image)
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
    def autoscaleChange(self, state):
        if (state == Qt.Checked):
            self.autoscale_brightness = True
        else:
            self.autoscale_brightness = False
        return

    ## ===================================
    def saturationCheckChange(self, state):
        self.saturated = (self.image >= self.cam_saturation_level)
        self.img_has_saturation = self.saturated.any()
        return

    ## ===================================
    def initialize_camera(self):
        try:
            self.camera_system = PySpin.System.GetInstance()
        except:
            return

        # Retrieve list of cameras from the system
        self.camera_list = self.camera_system.GetCameras()
        self.ncameras = self.camera_list.GetSize()
        print(f'Number of cameras detected: {self.ncameras}')

        if (self.ncameras == 0):
            self.outputbox.appendPlainText(f'No cameras detected!')
            return

        self.camera = self.camera_list[0]
        self.nodemap_tldevice = self.camera.GetTLDeviceNodeMap()
        self.camera.Init()                              ## Initialize the camera
        self.nodemap = self.camera.GetNodeMap()         ## Retrieve the camera's GenICam nodemap

        ## Initialize the camera to start up with full image size.
        fsl.set_full_imagesize(self.nodemap)

        ## The acquisition mode should be set to "SingleFrame" not "Continuous".
        #fsl.set_acquisition_mode(self.nodemap, "SingleFrame")

        if not fsl.set_autoexposure_off(self.nodemap, verbose=False):
            self.outputbox.appendPlainText(f'Failed to turn autoexposure off!')

        ## If "exposure compensation" exists on this camera, then turn it off. If it doesn't exist, then skip.
        if not fsl.set_exposure_compensation_off(self.nodemap, verbose=False):
            pass

        if not fsl.set_pixel_format(self.nodemap, 'Mono16', verbose=False):
            self.outputbox.appendPlainText(f'Failed to set the pixel format to Mono16!')

        if not fsl.set_binning(self.nodemap, self.binning, verbose=False):
            self.outputbox.appendPlainText(f'Failed to set the pixel binning to {self.binning}!')

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

        ## Make sure the gamma setting is turned off.
        #fsl.disable_gamma(self.nodemap)

        self.acquire_new_image()

        return

    ## ===================================
    def update_image_params(self):
        if self.image is None:
            return

        (self.Nx, self.Ny) = self.image.shape
        self.image_counter += 1

        ## Since we have a new image, we need to update the saturation flags.
        if self.saturation_checkbox.isChecked():
            self.saturated = (self.image >= self.cam_saturation_level)
            self.img_has_saturation = self.saturated.any()

        ## Make an 8-bit image object for display purposes. Set saturated pixels to red.
        if (self.img8bit is None) or (self.img8bit.shape != self.image.shape):
            self.img8bit = zeros((self.Nx,self.Ny,3), 'uint8')

        if not self.autoscale_brightness:
            self.img8bit[:,:,0] = self.image // self.tone_mapping_scale
            self.img8bit[:,:,1] = self.img8bit[:,:,0]
            self.img8bit[:,:,2] = self.img8bit[:,:,0]
        else:
            scaled_image = self.image - amin(self.image)
            scaled_image = 255.0 * scaled_image / amax(self.image)
            self.img8bit[:,:,0] = uint8(scaled_image)
            self.img8bit[:,:,1] = self.img8bit[:,:,0]
            self.img8bit[:,:,2] = self.img8bit[:,:,0]

        if self.saturation_checkbox.isChecked() and self.img_has_saturation:
            self.img8bit[self.saturated,0] = 255
            self.img8bit[self.saturated,1] = 0
            self.img8bit[self.saturated,2] = 0

        self.qimg = QImage(self.img8bit, self.Ny, self.Nx, QImage.Format_RGB888)
        self.pixmap = QPixmap.fromImage(self.qimg)
        #print('original pixmap_rect =', self.pixmap.rect())
        self.pixmap = self.pixmap.scaled(self.gui_width, self.gui_height-100, aspectRatioMode=Qt.KeepAspectRatio)
        #print('scaled pixmap_rect =', self.pixmap.rect())
        self.image_widget.setPixmap(self.pixmap)
        #print(f'self.gui_width,height = ({self.mainframe.rect().width()},{self.mainframe.rect().height()}  :  image_widget_width,height = {self.image_widget.width()},{self.image_widget.height()}')

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

            self.statusbar.showMessage(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')
            self.update_image_params()

        if self.live_checkbox.isChecked() and (self.ncameras > 0):
            ## Emit a signal to repeat this action after some ms defined by self.timer_delay.
            QTimer.singleShot(self.timer_delay, self.acquire_new_image)

        return

    ## ===================================
    def frameRateChange(self):
        if (self.ncameras == 0) or (self.framerate_spinbox.value() == 0):
            return

        new_framerate = self.framerate_spinbox.value()
        current_framerate = self.framerate
        if (abs(new_framerate - current_framerate) < 0.1):
            self.outputbox.appendPlainText(f'Failed to set framerate!')
            return
        else:
            fsl.set_framerate(self.nodemap, new_framerate)
            self.framerate = new_framerate
            self.outputbox.appendPlainText(f'Framerate set to {new_framerate} Hz')

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
        if (self.ncameras == 0) or not self.live_checkbox.isChecked():
            return

        new_exposure = self.exposure_spinbox.value()
        if (new_exposure > self.max_exposure):
            new_exposure = self.max_exposure
        if (new_exposure < self.min_exposure):
            new_exposure = self.min_exposure

        self.exposure = new_exposure
        self.exposure_spinbox.setValue(new_exposure)
        fsl.set_exposure_time(self.nodemap, new_exposure)
        self.outputbox.appendPlainText(f'Setting exposure = {self.exposure} usec')

        return

    ## ===================================
    def gainChange(self):
        if (self.ncameras > 0) and self.live_checkbox.isChecked():
            self.cam_gain = self.cam_gain_spinbox.value()
            fsl.set_gain(self.cam_gain)
        return

    ## ===================================
    def navgsChange(self, state):
        self.navgs = self.cam_navgs_spinbox.value()
        self.outputbox.appendPlainText(f'Setting navgs = {self.navgs}')
        return

    ## ===================================
    def fileOpen(self):
        (filename, ok) = QFileDialog.getOpenFileName(self, 'Load an image', '', 'Images (*.png *.jpg *.tif *.tiff *.npz, *.raw)')
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

            self.update_image_params()

        return

    ## ===================================
    def fileSave(self, filename='', scale=1, verbose=True):
        if not filename:
            (filename,ok) = QFileDialog.getSaveFileName(self, "Save image to a file", '000000.tif')
            if not filename:
                return

        suffix = os.path.splitext(filename)[1][1:]

        if verbose:
            self.outputbox.appendPlainText(f'Saving "{filename}"')

        ## Currently I don't have saving to *.raw format working for single frames. Redirect to these to *.tif.

        try:
            if suffix in ('jpg','png'):
                img8bit = uint8(self.image[::-1,:] * 255.0 / amax(self.image))
                imsave(filename, img8bit)
            elif suffix in ('tif','tiff'):
                imsave(filename, self.image[::-1,:] // scale)
            elif suffix == 'raw':
                new_filename = filename[:-4]+'.tif'
                self.outputbox.appendPlainText(f'Saving to RAW is not yet available for single frames. Changing to TIF: "{new_filename}"')
                imsave(new_filename, self.image[::-1,:] // scale)
            elif suffix == 'npz':
                savez(filename, image=self.image // scale)

            self.file_counter += 1
        except Exception as err:
            self.outputbox.appendPlainText(f'Failed to save image! Error message:\n    {err}')

        return

    ## ===================================
    def capture_image(self, nframes=1, verbose=False):
        if not hasattr(self, 'camera'):
            return(None)

        ## "scale" is used to divide the 16-bit image value by 16 to remove the 4 extra bits going from 16-bit to 12-bit data.
        ## However, if binning is turned on, then the sensor will deliver more than 12 bits.
        scale = 16 / (self.binning**2)

        if (nframes == 1):
            if (self.navgs == 1):
                (self.image, self.ts) = fsl.acquire_one_image(self.camera, self.nodemap)
                if self.image is None:
                    return(None)
                self.image = self.image // scale
            elif (self.navgs > 1):
                (img_set, ts_set) = fsl.acquire_num_images(self.camera, self.nodemap, self.navgs)
                if img_set is None:
                    return(None)
                self.image = uint32(mean(img_set, axis=2)) // scale
                self.ts = ts_set[0]
            return(self.image)
        elif (nframes > 1):
            if (self.navgs == 1):
                video = zeros((self.Nx,self.Ny,nframes), 'uint16')
                for n in range(nframes):
                    (self.image, self.ts) = fsl.acquire_one_image(self.camera, self.nodemap)
                    if self.image is None:
                        return(None)
                    video[:,:,n] = self.image // scale
            elif (self.navgs > 1):
                ## Save N frames and average them together to each one frame of the video.
                video = zeros((self.Nx,self.Ny,nframes), 'uint16')

                for n in range(nframes):
                    (img_set, ts_set) = fsl.acquire_num_images(self.camera, self.nodemap, self.navgs)
                    if img_set is None:
                        return(None)
                    self.image = uint32(mean(img_set, axis=2)) // scale
                    self.ts = ts_set[0]
                    video[:,:,n] = self.image

            return(video)
        else:
            raise ValueError('How did we get here?')

        return(None)

    ## ===================================
    def saveDirChanged(self, text):
        ## If the basename of the file to save has changed, then reset the file counter.
        self.file_counter = 0
        return

    ## ===================================
    def savePrefixChanged(self, text):
        ## If the basename of the file to save has changed, then reset the file counter.
        self.file_counter = 0
        return

    ## ===================================
    def saveSuffixChanged(self, text):
        ## If the basename of the file to save has changed, then reset the file counter.
        self.file_counter = 0
        return

    ## ===================================
    def save_video_sequence(self):
        nframes = self.save_nframes_spinbox.value()

        file_dir = self.file_dir_editbox.text()
        if not file_dir:
            file_dir = self.cwd
        elif (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_dir = file_dir.replace('\\', '/')
        if not file_dir.endswith('/'):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        if (nframes == 1):
            ## Note: the "file_counter" is what we use to keep track of all images saved so far in this session, so that we don't
            ## overwrite previous files. The "fileSave()" function keeps track of incrementing this value each time it is called.
            filename = f'{file_dir}{file_prefix}_{self.file_counter:05}.{file_suffix}'
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
                    filename = f'{file_dir}{file_prefix}_{self.file_counter:05}.{file_suffix}'
                    self.fileSave(filename, scale=16)
                self.outputbox.appendPlainText('Video save done.\n')

            if initial_state_is_live:
                self.live_checkbox.setChecked(True)

        return

    ## ===================================
    def fastsave_video(self):
        nframes = self.save_nframes_spinbox.value()

        file_dir = self.file_dir_editbox.text()
        if not file_dir:
            file_dir = self.cwd
        elif (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_dir = file_dir.replace('\\', '/')
        if not file_dir.endswith('/'):
            file_dir += '/'

        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        if (nframes == 1):
            ## Note: the "file_counter" is what we use to keep track of all images saved so far in this session, so that we don't
            ## overwrite previous files. The "fileSave()" function keep track of incrementing this value each time it is called.
            filename = f'{file_dir}{file_prefix}_{self.file_counter:05}.{file_suffix}'
            self.fileSave(filename)
            return

        initial_state_is_live = self.live_checkbox.isChecked()
        if initial_state_is_live:
            self.live_checkbox.setChecked(False)

        result_str = fsl.video_fastsave(self.camera, self.nodemap, nframes, file_dir, file_prefix, file_suffix, start_num=self.file_counter, verbose=True)
        if result_str:
            result_str += 'Video save done.\n'
            self.outputbox.appendPlainText(result_str)

        self.file_counter += nframes

        if initial_state_is_live:
            self.live_checkbox.setChecked(True)

        return

    ## ===================================
    def convert_frames_to_movie(self):
        file_dir = self.file_dir_editbox.text()
        if not file_dir:
            file_dir = self.cwd
        elif (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_dir = file_dir.replace('\\', '/')
        if not file_dir.endswith('/'):
            file_dir += '/'

        file_suffix = self.file_suffix_editbox.text()
        files = sort(glob(f'{file_dir}*.{file_suffix}'))
        if (len(files) == 0):
            self.outputbox.appendPlainText(f'No "{file_suffix}" files found in folder "{file_dir}"')
            return

        ## Collect a list of the image frames to generate the video. Not the fastest way to do this, but it's probably
        ## not a time-sensitive thing.
        image_list = []
        for file in files:
            if (file_suffix == 'raw'):
                img = fsl.read_binary_image(file, self.Nx, self.Ny)
            else:
                img = imread(file)

            image_list.append(img)

        ## Use matplotlib to animate the frames.
        import matplotlib.animation as animation
        frame_list = []         # for storing the generated figure frames
        fig = plt.figure(figsize=(18,15))
        plt.tight_layout()
        for i in range(len(files)):
            frame_list.append([plt.imshow(image_list[i], cmap='gray', animated=True)])

        true_framerate = fsl.get_framerate(self.nodemap)
        replay_framerate = 15.0
        ani = animation.ArtistAnimation(fig, frame_list, interval=int(1000.0/framerate), blit=True, repeat_delay=1000)
        ani.save('movie.mp4')

        return

    ## ===================================
    def do_autoexposure(self, button_info, verbose=True):
        if (self.ncameras == 0) or not self.live_checkbox.isChecked():
            self.outputbox.appendPlainText(f'Cannot do autoexposure when the camera is not live!')
            return

        ## Set the exposure so that the maximum brightness pixel is at 98% of saturation. If there are not saturated pixels in the image, then this is easy.
        ## If there are saturated pixels, then we first have to reduce the exposure so that they are not saturated and then do the linear exposure scaling.
        while self.img_has_saturation:
            self.exposure /= 2
            self.exposure_spinbox.setValue(self.exposure)
            fsl.set_exposure_time(self.nodemap, self.exposure)
            self.acquire_new_image()
            if (self.image is None):
                self.outputbox.appendPlainText(f'Failed to capture an image. Aborting...')
                return(False)

            ## If the checkbox is not checked, then "acquire_new_image()" will not update the "img_has_saturation" variable.
            if self.saturation_checkbox.isChecked():
                self.saturated = (self.image >= self.cam_saturation_level)
                self.img_has_saturation = self.saturated.any()

        self.exposure = uint32(self.exposure * self.cam_saturation_level * 0.98 / amax(self.image))
        if verbose:
            self.outputbox.appendPlainText(f'Set optimized exposure time to {self.exposure}ms')
        self.exposure_spinbox.setValue(self.exposure)
        fsl.set_exposure_time(self.nodemap, self.exposure)
        return(True)

    ## ===================================
    def binningChange(self):
        if (self.ncameras == 0):
            return

        if not fsl.set_binning(self.nodemap, self.binning_spinbox.value()):
            self.outputbox.appendPlainText(f'Failed to set the binning value!')
            return

        self.binning = self.binning_spinbox.value()
        ## Now that the binning has changed, modify the image size, and update the statusbar string.
        (self.Ny,self.Nx) = fsl.get_image_width_height(self.nodemap, verbose=False)
        self.statusbar.showMessage(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')
        self.outputbox.appendPlainText(f'Setting binning = {self.binning}. Now the image dims = ({self.Nx},{self.Ny})')

        ## Modify the saturation values, and the colorbar maxval.
        self.cam_bitdepth = 12 + uint16(log2(self.binning**2))      ## camera bit depth
        self.cam_saturation_level = (2**self.cam_bitdepth) - 2
        self.tone_mapping_scale = uint16(pow(2.0, self.cam_bitdepth - 8))

        return

    ## ===================================
    def croppingChange(self):
        if (self.ncameras == 0):
            return

        self.cropping = self.binning_spinbox.value()

        if (self.cropping == 0):
            set_height = self.image_maxheight
            set_width = self.image_maxwidth
        elif (self.cropping == 1):
            set_height = self.image_maxheight // 2
            set_width = self.image_maxwidth // 2
        elif (self.cropping == 2):
            set_height = self.image_maxheight // 4
            set_width = self.image_maxwidth // 4
        elif (self.cropping == 3):
            set_height = self.image_maxheight // 8
            set_width = self.image_maxwidth // 8

        ## Since we are forcing the cropping to be centered, the offsets are not free variables, but are determined by the size of the cropped image.
        set_height_offset = (self.image_maxheight // 2) - (set_height // 2)
        set_width_offset = (self.image_maxwidth // 2) - (set_width // 2)

        if not fsl.set_image_region(self.nodemap, set_height, set_width, set_height_offset, set_width_offset):
            self.outputbox.appendPlainText(f'Failed to set the cropping value!')
            return
        self.outputbox.appendPlainText(f'Setting cropping = {self.cropping}')

        ## Now that the cropping has changed, modify the image size, and update the statusbar string.
        (self.Ny,self.Nx) = fsl.get_image_width_height(self.nodemap, verbose=False)
        self.statusbar.showMessage(f'image size: img(Nx,Ny) = ({self.Nx},{self.Ny}),     image_counter = {self.image_counter}')

        return

    ## ===================================
    def show_histogram(self):
        self.outputbox.appendPlainText(f'Histogram function is not yet implemented')
        return

    ## ===================================
    def image_clicked(self, event):
        if (event.button() == 1):
            self.outputbox.appendPlainText("Left button clicked")
        elif (event.button() == 2):
            self.outputbox.appendPlainText("Right button clicked")

        live_data_state = self.live_checkbox.isChecked()
        self.live_checkbox.setChecked(False)
        self.dlg = CustomDialog(self.image)
        self.dlg.exec()
        self.live_checkbox.setChecked(live_data_state)
        return

    ## ===================================
    def activate_projector(self):
        if self.has_fpp:
            return

        from device_projector import fpp_projector

        try:
            self.fpp_projector_obj = fpp_projector()
            self.proj = self.fpp_projector_obj.proj
        except ValueError as err:
            self.outputbox.appendPlainText(f'Error: {err}')
            return

        self.fpp_nphases = 4            ## the number of pattern images to use for estimating phase
        self.fpp_nfringes = 16          ## the number of fringes to project across the image
        self.fpp_phasenum = 0           ## the number of the current projection pattern (from 0 to [1-self.nphases])

        ## Ask for the pixel dimensions of the monitor/projector/SLM display.
        self.outputbox.appendPlainText(f'Projecting an ({self.fpp_projector_obj.Nx},{self.fpp_projector_obj.Ny}) image.')

        ## Make a set of coordinates for generating the fringe patterns for projection.
        (self.proj_xcoord,self.proj_ycoord) = indices((self.fpp_projector_obj.Nx,self.fpp_projector_obj.Ny))

        self.update_projector_pattern()
        self.has_fpp = True
        self.save_fppdata_button.setEnabled(True)

        return

    ## ===================================
    def update_projector_pattern(self):
        ## If the current phase is equal to "nphases" then this is the same thing as setting it to zero.
        if (self.fpp_phasenum >= self.fpp_nphases):
            self.fpp_phasenum = 0

        k = 2.0 * pi * self.fpp_nfringes / self.fpp_projector_obj.Ny
        phi_shift = 2.0 * pi * self.fpp_phasenum / self.fpp_nphases

        ## Generate the sinusoidal fringe pattern. Note that this has to be uint8.
        self.proj_img = uint8(rint(255.0*(0.5 + 0.5*cos(k*self.proj_ycoord + phi_shift))))

        ## Send this image to the monitor/projector/SLM.
        self.fpp_projector_obj.project_pattern(self.proj_img)

        return

    ## ===================================
    def collect_fpp_imageset(self):
        file_dir = self.file_dir_editbox.text()
        if file_dir and (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        for n in range(self.fpp_nphases):
            self.fpp_phasenum = n
            phasevalue_deg = int(rint(360.0 * self.fpp_phasenum / self.fpp_nphases))
            self.update_projector_pattern()
            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            filename = f'{file_dir}{file_prefix}_{phasevalue_deg:03}.{file_suffix}'
            self.fileSave(filename)

        ## Return to the phase zero position.
        self.fpp_phasenum = 0
        self.update_projector_pattern()
        self.outputbox.appendPlainText(f'FPP image collection is complete.')

        return

    ## ===================================
    def activate_lctf(self):
        if self.has_lctf:
            return

        from device_kurios import KuriosLCTFdevice

        try:
            self.lctf_device_handle = KuriosLCTFdevice()
        except Exception as err:
            self.outputbox.appendPlainText(f'Failed to find an LCTF. Aborting initialization...')
            return

        self.has_lctf = True
        self.save_lctfdata_button.setEnabled(True)

        return

    ## ===================================
    def set_lctf_wavelength(self, new_wavelength):
        if self.lctf_device_handle.set_wavelength(new_wavelength):
            self.lctf_currentwave = new_wavelength
        else:
            self.outputbox.appendPlainText(f'Failed to set the LCTF wavelength to {new_wavelength}nm.')
        return

    ## ===================================
    def collect_lctf_imageset(self):
        file_dir = self.file_dir_editbox.text()
        if file_dir and (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        self.lctf_wavelist = uint16(linspace(430,650,20))     ## returns a list from 430 to 720 in increments of 10
        self.lctf_wave_counter = 0          ## counter for which element of wavelist is the current one

        for wave_nm in self.lctf_wavelist:
            self.set_lctf_wavelength(wave_nm)

            ## Check image exposure time here.
            ok = self.do_autoexposure(None, verbose=False)
            if not ok:
                self.outputbox.appendPlainText(f'Failed collection sequence!')
                return

            self.outputbox.appendPlainText(f'{wave_nm}nm: set optimized exposure time to {self.exposure}ms')
            time.sleep(0.2)

            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            ## Actually, I really should be saving the exposure time too, in order to keep track of changes.
            filename = f'{file_dir}{file_prefix}_{wave_nm:03}.{file_suffix}'
            self.fileSave(filename)
            time.sleep(0.2)

        ## Return to the 550nm default wavelength.
        self.set_lctf_wavelength(550)
        self.outputbox.appendPlainText(f'LCTF image collection is complete.')

        return

    ## ===================================
    def activate_motor(self):
        if self.has_motor:
            return

        from device_k10cr1 import thorlabs_motor

        self.outputbox.appendPlainText(f'Initializing the motor.\nThis may take a minute...')
        time.sleep(1.0)     ## Give time for the above message to appear before starting to initialize, else it shows up only after initializing is done
        try:
            self.k10cr1_motor_obj = thorlabs_motor()
        except Exception as err:
            self.outputbox.appendPlainText(f'Failed to find a motor. Aborting initialization...')
            return

        self.motor = self.k10cr1_motor_obj.motor
        self.has_motor = True
        self.save_hurlbut_data_button.setEnabled(True)

        return

    ## ===================================
    def collect_hurlbut_filter_imageset(self):
        file_dir = self.file_dir_editbox.text()
        if file_dir and (file_dir[-1] not in ('/','\\')):
            file_dir += '/'
        file_prefix = self.file_prefix_editbox.text()
        file_suffix = self.file_suffix_editbox.text()

        self.nangles = 10
        self.angle_stepsize = 5.0
        self.hurlbut_angles = arange(self.nangles) * self.angle_stepsize

        for a in self.hurlbut_angles:
            self.motor.move_to(a, blocking=True)
            #self.k10cr1_motor_obj.live_motion_monitor(a)
            img = self.capture_image(1)
            if img is None:
                self.outputbox.appendPlainText(f'Failed to collect an image!')
                return
            else:
                self.image = img

            filename = f'{file_dir}{file_prefix}_{a:03}.{file_suffix}'
            self.fileSave(filename)
            self.outputbox.appendPlainText(f'LCTF image collection is complete.')

        return

## ======================================================================================================
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
def clean_folders():
    folders = ['C:/Users/root/','C:/Users/root/Desktop/','C:/Users/root/Documents/','C:/Users/root/Pictures/']
    for folder in folders:
        files = glob(folder + '*.png') + glob(folder + '*.PNG')
        files += glob(folder + '*.jpg') + glob(folder + '*.JPG')
        files += glob(folder + '*.jpeg') + glob(folder + '*.JPEG')
        files += glob(folder + '*.bmp') + glob(folder + '*.BMP')
        files += glob(folder + '*.tif') + glob(folder + '*.TIF')
        files += glob(folder + '*.tiff') + glob(folder + '*.TIFF')
        files = unique(files)

        current_time = time.time()
        for f in files:
            file_creation_time = os.path.getctime(f)

            ## Delete any image files more than 18 hours old
            if (current_time - file_creation_time) / 3600 >= 18.0:
                print(f'Deleting "{f}" ...')
                os.unlink(f)

    return

## ======================================================================================================
## ======================================================================================================

if __name__ == '__main__':
    ## First thing. When booting up, we should delete any image files (TIFF, PNG, JPG, BMP) that are present in the
    ## following folders, as long as the files are 1 day or more old.
    ##      /Desktop, /Root, /Pictures, /Documents
    mpl.rcParams["savefig.directory"] = 'C:/Users/root/Desktop/'    ## default location to save figures
    #clean_folders()

    ## Start the camera GUI.
    app = QApplication(sys.argv)
    app.setApplicationName('Interactive Full-Stokes Video Camera')

    ## Calculate the current desktop screen size available. Store the results as global variables.
    screen = QApplication.primaryScreen()
    size = screen.size()
    print('Screen Size: %d x %d' % (size.width(), size.height()))
    rect = screen.availableGeometry()
    this_h = int(0.95*rect.height())
    this_w = int(0.95*rect.width())
    print('Available Size for GUI: %d x %d' % (this_w, this_h))

    mw = MainWindow(gui_height=this_h, gui_width=this_w)
    mw.setWindowTitle('Interactive Full-Stokes Video Camera')
    mw.setMinimumSize(this_w, this_h)
    mw.show()
    mw.acquire_new_image()
    sys.exit(app.exec_())       ## start the execution loop
