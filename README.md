# FLIR Camera Interface

A GUI interface for perating FLIR cameras via the Spinnaker SDK. The interface includes optional elements for simultaneously integrating the detection with (1) a display engine (for doing Fringe Projection Profilometry), (2) a Thorlabs liquid crystal tunable filter (LCTF, for doing spectral imaging).

## Requirements

The user must have FLIR's Spinnaker SDK installed, and have a camera that is operating via SpinView without problems.

Next, the user should copy the PySpin wheel file (this has a name like ``spinnaker_python-2.5.0.80-cp38-cp38-win_amd64.whl``) to a location where it can be reached with the terminal. Start up the Anaconda terminal and do the following:

    conda create -n pyspin python=3.8				## create the "pyspin" environment
    conda activate pyspin							## enter the new environment
    conda install numpy scipy matplotlib imagio	ffmpeg openh264	 ## install other packages you will need
    pip install --no-deps spinnaker_..._python.whl		## use your filename for the pyspin wheel file
    pip install --no-deps [other files]				## if you need to install anything else with pip, use this approach

Now you should be able to run ``flir_camera_interface.py`` file.

## Module files

``flir_camera_interface.py``: the GUI interface itself.

``flir_spin_library.py``: the library file, containing the scripts needed to get and set camera parameters.

``flir_print_camera_status.py``: a script that prints to stdout, showing the state of all GenICam variables available on the camera.

