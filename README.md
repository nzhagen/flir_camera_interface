---
# FLIR Camera Interface

A GUI interface for perating FLIR cameras via the Spinnaker SDK. The interface includes optional elements for simultaneously integrating the detection with (1) a display engine (for doing Fringe Projection Profilometry), (2) a Thorlabs liquid crystal tunable filter (LCTF, for doing spectral imaging).

## Requirements

The user must have FLIR's Spinnaker SDK installed, and have a camera that is operating via SpinView without problems.

Next, the user should copy the PySpin wheel file (this has a name like ``spinnaker_python-2.5.0.80-cp38-cp38-win_amd64.whl``) to a location where it can be reached with the terminal. Start up the Anaconda terminal and do the following:

    conda update -n base -c conda-forge conda     ## update conda before starting
    conda update --all                            ## and update all the packages too if you want
    conda create -n flir python=3.8               ## create the "flir" environment
    conda activate flir                           ## enter the new environment
    conda install numpy scipy matplotlib imageio  ## install other packages you will need
    conda install ffmpeg openh264                 ## you will need these if you want to generate videos
    pip install --no-deps spinnaker_..._python.whl		## use your filename for the pyspin wheel file
    pip install --no-deps [other files]				## if you need to install anything else with pip, use this approach

Now you should be able to run ``flir_camera_interface.py`` file.

## Module files

``flir_camera_interface.py``: the GUI interface itself.

``flir_spin_library.py``: the library file, containing the scripts needed to get and set camera parameters.

---
# Adding an auxiliary projector

If a projector is connected to the computer at the same time as the FLIR camera, the computer treats it as a second display. In order to control the projector while running the camera, we use the ``slmpy`` package to display an image on the "second monitor" (the projector). Implementing this requires first pushing the ``Activate FPP'' button the FLIR camera GUI, which turns on its neighbor button ``Save FPP Dataset``, and then click on that now-active button. In order to customize what happens when you push that button, modify the ``collect_fpp_imageset()`` function. The install process for getting the projector device running is:

    pip install --no-deps slmpy
    conda install wxpython              ## I often have trouble getting conda to succeed here
    pip install --no-deps wxpython      ## if the conda install doesn't work

---
# Adding a Kurios liquid crystal tunable filter

If a Kurios LCTF is connected to the computer at the same time as the FLIR camera, then we can interactively change the filter wavelength while collecting images. To do this, first click on the ``Activate LCTF'' button the FLIR camera GUI, which turns on its neighbor button ``Save LCTF Dataset``, and then click on that now-active button. In order to customize what happens when you push that button, modify the ``collect_lctf_imageset()`` function.

In order to install the LCTF and get it connected, first download and install Thorlabs' software, ``Kurios1.6.3.exe''. This generates a folder (you can access it from the ``Thorlabs`` entry in the Start Menu) that contains the following files:

    KURIOS_COMMAND_LIB_Win64.dll
    KURIOS_COMMAND_LIB.py

If you do not have these in your repository, move them into a subfolder named "devices/". In addition, you should have there a Python file named ``device_kurios.py''. This should be moved into the "devices/" folder as well. As long as your Python script can find these files, it should run okay.

Note: Thorlabs has a bug in their EXE such that the _Win32.dll file shows in the Python SDK folder, but not the _Win64.dll file. You can find the latter in the C/C++ SDK folder instead.

---
# Adding a Thorlabs K10CR1 rotation stage

If a Thorlabs K10CR1 rotational stage is connected to the computer at the same time as the FLIR camera, then we can interactively rotate components while collecting images. To do this, first click on the ``Activate Motor'' button the FLIR camera GUI, which turns on its neighbor button ``Save Hurlbut Filter Dataset``, and then click on that now-active button. In order to customize what happens when you push that button, modify the ``collect_hurlbut_filter_imageset()`` function.

In order to install the K10CR1 stage and get it connected, first download and install Thorlabs' APT software, which includes the file ``APT.dll`` that can be found in the ``C:/Program Files/Thorlabs/APT/APT Server/`` folder. Download the ``thorlabs_apt`` software repository located at

    https://github.com/qpit/thorlabs_apt

then, at the command line in that repository's base folder, run the command

    python setup.py install

If there is an error, you may need to replace the dash in the ``setup.cfg`` file with an underscore. Next, copy the ``APT.dll`` file to the flir camera interface's "device/" subfolder. That should be all you need.

