# FLIR Camera Interface

A GUI interface for perating FLIR cameras via the Spinnaker SDK. The interface includes optional elements for simultaneously integrating the detection with (1) a display engine (for doing Fringe Projection Profilometry), (2) a Thorlabs liquid crystal tunable filter (LCTF, for doing spectral imaging).

## Requirements

The user must have FLIR's Spinnaker SDK installed, and have a camera that is operating via SpinView without problems.

Next, the user should copy the PySpin wheel file (this has a name like ``spinnaker_python-2.5.0.80-cp38-cp38-win_amd64.whl``) to a location where it can be reached with the terminal. Start up the Anaconda terminal and do the following:

    conda update -n base -c conda-forge conda     ## update conda before starting
    conda update --all                            ## and update all the packages too if you want
    conda create -n pyspin python=3.8				## create the "pyspin" environment
    conda activate pyspin							## enter the new environment
    conda install numpy scipy matplotlib imageio ffmpeg openh264	 ## install other packages you will need
    pip install --no-deps spinnaker_..._python.whl		## use your filename for the pyspin wheel file
    pip install --no-deps [other files]				## if you need to install anything else with pip, use this approach

Now you should be able to run ``flir_camera_interface.py`` file.

## Module files

``flir_camera_interface.py``: the GUI interface itself.

``flir_spin_library.py``: the library file, containing the scripts needed to get and set camera parameters.

``flir_print_camera_status.py``: a script that prints to stdout, showing the state of all GenICam variables available on the camera.

# Adding an auxiliary projector

If a projector is connected to the computer at the same time as the FLIR camera, the computer treats it as a second display. In order to control the projector while running the camera, we use the ``slmpy`` package to display an image on the "second monitor" (the projector). Implementing this requires first pushing the ``Activate FPP'' button the FLIR camera GUI, which turns on the neighboring button, and then use the now-active ``Save FPP Dataset`` button. In order to customize what happens when you push that button, modify the ``collect_fpp_imageset()`` function. The install process for getting the projector device running is:

    pip install --no-deps slmpy
    conda install wxpython              ## I often have trouble getting conda to succeed here
    pip install --no-deps wxpython      ## if the conda install doesn't work

