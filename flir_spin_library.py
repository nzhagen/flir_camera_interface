import os
import sys
import PySpin
from numpy import empty, amin, amax, array, zeros, arange, uint16
import struct

# *** NOTES ***
# 
# The naming convention of QuickSpin enumerations is the name of the
# enumeration node followed by an underscore and the symbolic of
# the entry node. Selecting "Off" on the "ExposureAuto" node is
# thus named "ExposureAuto_Off".
#
# Grabbing node information requires first retrieving the node and
# then retrieving its information. There are two things to keep in
# mind. First, a node is distinguished by type, which is related
# to its value's data type. Second, nodes should be checked for
# availability and readability/writability prior to making an
# attempt to read from or write to the node.
#
# Numeric nodes have both a minimum and maximum. A minimum is retrieved
# with the method GetMin(). Sometimes it can be important to check
# minimums to ensure that your desired value is within range.
#
# It is often desirable to check the increment as well. The increment
# is a number of which a desired value must be a multiple of. Certain
# nodes, such as those corresponding to offsets X and Y, have an
# increment of 1, which basically means that any value within range
# is appropriate. The increment is retrieved with the method GetInc().
#
# Other nodes, such as those corresponding to image width and height,
# might have an increment other than 1 (if binning is turned on). In these cases, it can be
# important to check that the desired value is a multiple of the
# increment. However, as these values are being set to the maximum,
# there is no reason to check against the increment.
#
# A maximum is retrieved with the method GetMax(). The value retrieved for a node's minimum and
# maximum should always be a multiple of its increment.
#
#  Setting the value of an enumeration node is more complicated
#  than other node types. Two nodes must be retrieved: first, the
#  enumeration node is retrieved from the nodemap; and second, the entry
#  node is retrieved from the enumeration node. The integer value of the
#  entry node is then set as the new value of the enumeration node.
#
#  What happens when the camera begins acquiring images depends on the
#  acquisition mode. Single frame captures only a single image, multi
#  frame captures a set number of images, and continuous captures a
#  continuous stream of images. Because the example calls for the
#  retrieval of 10 images, continuous mode has been set.
#
#  Capturing an image houses images on the camera buffer. Trying
#  to capture an image that does not exist will hang the camera.
#  Once an image from the buffer is saved and/or no longer
#  needed, the image must be released in order to keep the
#  buffer from filling up.
#
#  For Spinnaker's image Save() function, the allowed image formats (extensions) are:
#       PGM       Portable gray map.
#       PPM       Portable pixmap.
#       BMP       Bitmap.
#       JPEG      JPEG.
#       JPEG2000  JPEG 2000.
#       TIFF      Tagged image file format.
#       PNG       Portable network graphics.
#       RAW    	  Raw data.
#       JPEG12_C  12 bit compressed JPEG data. 

## ====================================================================================
def truncate_multiple(value, increment):
    trunc_value = increment * (value // increment)
    return(trunc_value)

## ===============================================================================================
def read_binary_image(filename, Nx, Ny):
    ## Read an image file saved in Spinnaker's binary format. Assumes fmt=uint16.
    with open(filename, 'rb') as fileobj:
        raw = fileobj.read()

    buffersize = len(raw)

    bytesize = 2
    img = zeros((Nx,Ny), 'uint16')
    q = 0

    xvalues = Nx - 1 - arange(Nx)
    for x in xvalues:
        try:
            row = uint16(struct.unpack(('<'+str(Ny)+'H').encode('ascii'), raw[q:q+(Ny*bytesize)]))
        except Exception as e:
            raise ImportError('Cannot decode datacube: ' + repr(e))
        img[x,:] = row
        q += Ny * bytesize

    return(img)

## ====================================================================================
def set_exposure_time(nodemap, time_in_usec, verbose=False):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param nodemap: Device GenICam nodemap
     :type nodemap: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    ## Set exposure time manually. Automatic exposure prevents the manual configuration of exposure
    ## times and needs to be turned off for manual setting to work.

    try:
        result = True

        node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
        if not PySpin.IsAvailable(node_exposure_auto) and PySpin.IsWritable(node_exposure_auto):
            print('Autoexposure node is not available.')
            return(False)

        value = node_exposure_auto.GetIntValue()     ## 0='Off', 2='Continuous'
        if verbose:       ## if you want to get the *name* of the autoexposure setting, then try this block
            node_enum_entry = node_exposure_auto.GetCurrentEntry()
            display_name = node_enum_entry.GetDisplayName()
            print(f'AutoExposure is {display_name}')

        if (value != 0):
            node_exposure_auto.SetIntValue(2)
            if verbose:       ## if you want to get the *name* of the autoexposure setting, then try this block
                print('Turning off AutoExposure ...')
        
        node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode('ExposureTime'))
        if not PySpin.IsAvailable(node_exposure_time) and PySpin.IsReadable(node_exposure_time):
            print('ExposureTime node is not available.')
            return(False)

        min_exposure_time = node_exposure_time.GetMin()
        max_exposure_time = node_exposure_time.GetMax()
        set_time = max((time_in_usec, min_exposure_time))
        set_time = min((set_time, max_exposure_time))
        node_exposure_time.SetValue(set_time)
        
        if verbose:
            print(f'Exposure time: limits = ({min_exposure_time:.1f},{max_exposure_time:.1f}), value set to {node_exposure_time.GetValue():.1f} usec ...')
    except PySpin.SpinnakerException as ex:
        print('set_exposure_time() Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def set_autoexposure_off(nodemap, verbose=False):
    """
    This function temporarily disables automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
 
    try:
        result = True

        node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
        if not PySpin.IsAvailable(node_exposure_auto) and PySpin.IsWritable(node_exposure_auto):
            print('Autoexposure node is not available.')
            return(False)

        node_exposure_auto_off = node_exposure_auto.GetEntryByName("Off")
        if not PySpin.IsAvailable(node_exposure_auto_off) and PySpin.IsReadable(node_exposure_auto_off):
            print('Autoexposure_off node is not available.')
            return(False)
        
        node_exposure_auto.SetIntValue(node_exposure_auto_off.GetValue())
        if verbose:
            print('Turning auto-exposure off')
    except PySpin.SpinnakerException as ex:
        print('set_autoexposure_off() Error: %s' % ex)
        result = False

    return result

## ====================================================================================
def set_autoexposure_on(nodemap, verbose=False):
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
        if not PySpin.IsAvailable(node_exposure_auto) and PySpin.IsWritable(node_exposure_auto):
            print('Autoexposure node is not available.')
            return(False)

        node_exposure_auto_on = node_exposure_auto.GetEntryByName("Continuous")
        if not PySpin.IsAvailable(node_exposure_auto_on) and PySpin.IsReadable(node_exposure_auto_on):
            print('Autoexposure_continuous node is not available.')
            return(False)
        
        node_exposure_auto.SetIntValue(node_exposure_auto_on.GetValue())
        if verbose:
            print('Turning auto-exposure on')
    except PySpin.SpinnakerException as ex:
        print('set_autoexposure_on() Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def set_pixel_format(nodemap, pixfmt, verbose=False):
    """
    Configures the camera pixel format. This must be applied before BeginAcquisition()
    is called; otherwise, they will be read only. Also, it is important to note that
    settings are applied immediately. This means if you plan to reduce the width and
    move the x offset accordingly, you need to apply such changes in the appropriate order.

    :param nodemap: Device GenICam nodemap
    :type nodemap: INodeMap
    :param pixelformat: String, options are: ['Mono8', 'Mono12', 'Mono16']
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Apply pixel format
    #
    # *** NOTES ***
    # Enumeration nodes are slightly more complicated to set than other
    # nodes. This is because setting an enumeration node requires working
    # with two nodes instead of the usual one.
    #
    # As such, there are a number of steps to setting an enumeration node:
    # retrieve the enumeration node from the nodemap, retrieve the desired
    # entry node from the enumeration node, retrieve the integer value from
    # the entry node, and set the new value of the enumeration node with
    # the integer value from the entry node.

    try:
        result = True

        # Retrieve the enumeration node from the nodemap
        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
        if PySpin.IsAvailable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):

            # Retrieve the desired entry node from the enumeration node
            if (pixfmt == 'Mono8'):
                node_pixel_format_mono = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono8'))
            elif (pixfmt == 'Mono12p'):
                node_pixel_format_mono = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono12p'))
            elif (pixfmt == 'Mono16'):
                node_pixel_format_mono = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('Mono16'))
            else:
                print(f'Cannot recognize pixel format "{pixfmt}"...')
                return(False)

            if PySpin.IsAvailable(node_pixel_format_mono) and PySpin.IsReadable(node_pixel_format_mono):

                # Retrieve the integer value from the entry node
                pixel_format_mono = node_pixel_format_mono.GetValue()

                # Set integer as new value for enumeration node
                node_pixel_format.SetIntValue(pixel_format_mono)

                if verbose:
                    print(f'Pixel format set to {node_pixel_format.GetCurrentEntry().GetSymbolic()}')
            else:
                print('Pixel format node not available...')
        else:
            print('Pixel format node not available...')

    except PySpin.SpinnakerException as ex:
        print('set_pixel_format() Error: %s' % ex)
        return(False)

    return(result)

## ====================================================================================
def set_image_region(nodemap, height, width, height_offset, width_offset, verbose=False):
    """
    Configures the width, height, width offset, and height offset. These settings must be applied before 
    BeginAcquisition() is called; otherwise, they will be read only. Also, it is important to note that
    settings are applied immediately. This means if you plan to reduce the width and move the x offset 
    accordingly, you need to apply such changes in the appropriate order.

    :param nodemap: Device GenICam nodemap
    :param height: uint
    :param width: uint
    :param height_offset: uint
    :param width_offset: uint
    :type nodemap: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        # *** NOTES ***
        # If, say, the image size is full, then you can't set the offsets to larger than 0 until you first reduce the
        # image size. Or, if the offsets are nonzero and you want to return to full image size, then you first have
        # to reduce the offsets to zero before setting the image size. So here is an always-safe procedure:
        # (1) set the offsets temporarily to 0, (2) set the image sizes, (3) if the offsets are > 0, then now set them.

        # Apply minimum offset X
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
            min_width_offset = node_offset_x.GetMin()
            node_offset_x.SetValue(min_width_offset)
        else:
            print('Offset X node not available...')

        # Apply minimum to offset Y
        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
            min_height_offset = node_offset_y.GetMin()
            node_offset_y.SetValue(min_height_offset)
        else:
            print('Offset Y node not available...')

        ## Set image width. Find out what the image pixel increment value is. Then you can check to see if the set 
        ## value is a proper integer multiple of the increment before trying to set the value.
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('WidthMax'))
        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
            min_width = node_width.GetMin()
            max_width = node_width.GetMax()
            width_incr = node_width.GetInc()
            set_width = truncate_multiple(width, width_incr)
            set_width = max((set_width, min_width))
            set_width = min((set_width, max_width))
            node_width.SetValue(set_width)
            if verbose:
                print(f'Image width: limits = ({min_width},{max_width}), value set to {node_width.GetValue()}...')
        else:
            print('Image width node not available...')

        ## Set image height
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('HeightMax'))
        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
            min_height = node_height.GetMin()
            max_height = node_height.GetMax()
            height_incr = node_height.GetInc()
            set_height = truncate_multiple(height, height_incr)
            set_height = max((set_height, min_height))
            set_height = min((set_height, max_height))
            node_height.SetValue(set_height)
            if verbose:
                print(f'Image height: limits = ({min_height},{max_height}), value set to {node_height.GetValue()}...')
        else:
            print('Image height node not available...')

        ## Apply offset X
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        if (width_offset > min_width_offset) and PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
            max_width_offset = node_offset_x.GetMax()
            set_width_offset = min((width_offset, max_width_offset))
            node_offset_x.SetValue(set_width_offset)
            if verbose:
                print(f'Width offset: limits = ({min_width_offset},{max_width_offset}), value set to {node_offset_x.GetValue()}...')
        else:
            print('Width offset node not available...')

        ## Apply minimum to offset Y
        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        if (height_offset > min_height_offset) and PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
            max_height_offset = node_offset_y.GetMax()
            set_height_offset = min((height_offset, max_height_offset))
            node_offset_y.SetValue(set_height_offset)
            if verbose:
                print(f'Height offset: limits = ({min_height_offset},{max_height_offset}), value set to {node_offset_y.GetValue()}...')
        else:
            print('Height offset node not available...')
    except PySpin.SpinnakerException as ex:
        print('set_image_region() Error: %s' % ex)
        return(False)

    return(result)

## ====================================================================================
def set_full_imagesize(nodemap, verbose=False):
    """
    Sets the camera's width & height to be the maximum possible (no binning and no cropping). These settings must be 
    applied before BeginAcquisition() is called.

    :param nodemap: Device GenICam nodemap
    :param height: uint
    :param width: uint
    :param height_offset: uint
    :param width_offset: uint
    :type nodemap: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        ## First reset the binning value to 1.
        set_binning(nodemap, 1)

        ## Apply minimum offset X
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
            node_offset_x.SetValue(0)
        else:
            print('Offset X node not available...')

        ## Apply minimum to offset Y
        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
            node_offset_y.SetValue(0)
        else:
            print('Offset Y node not available...')

        ## Set image width. Find out what the image pixel increment value is. Then you can check to see if the set 
        ## value is a proper integer multiple of the increment before trying to set the value.
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
            node_width.SetValue(node_width.GetMax())
        else:
            print('Image width node not available...')

        ## Set image height
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
            node_height.SetValue(node_height.GetMax())
        else:
            print('Image height node not available...')

    except PySpin.SpinnakerException as ex:
        print('set_full_imagesize() Error: %s' % ex)
        return(False)

    return(result)

## ====================================================================================
def set_binning(nodemap, binning_value, verbose=False):
    """
    Set the camera binning.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :param binning_value: uint
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    ## Note that in some cameras the horizontal and vertical binning cannot be configured separately. In the
    ## FLIR cameras, in this case, the horizontal binning value is ignored, and the "vertical binning" controls
    ## the binning in both dimensions.
    try:
        result = True

        # Apply horizontal binning
        node_binning_h = PySpin.CIntegerPtr(nodemap.GetNode('BinningHorizontal'))
        if PySpin.IsAvailable(node_binning_h) and PySpin.IsWritable(node_binning_h):
            min_binning_h = node_binning_h.GetMin()
            max_binning_h = node_binning_h.GetMax()
            set_binning_h = max((binning_value, min_binning_h))
            set_binning_h = min((set_binning_h, max_binning_h))
            node_binning_h.SetValue(set_binning_h)
            if verbose:
                print(f'Horizontal binning: limits = ({min_binning_h},{max_binning_h}), value set to {node_binning_h.GetValue()}')
        else:
            ## Some cameras use the vertical binning to set the value for both horizontal and vertical.
            ## In that case, just ignore any problems with setting the horizontal one.
            pass
            #print('Horizontal binning node not available...')

        # Apply vertical binning
        node_binning_v = PySpin.CIntegerPtr(nodemap.GetNode('BinningVertical'))
        if PySpin.IsAvailable(node_binning_v) and PySpin.IsWritable(node_binning_v):
            min_binning_v = node_binning_v.GetMin()
            max_binning_v = node_binning_v.GetMax()
            set_binning_v = max((binning_value, min_binning_v))
            set_binning_v = min((set_binning_v, max_binning_v))
            node_binning_v.SetValue(set_binning_v)
            if verbose:
                print(f'Vertical binning: limits = ({min_binning_v},{max_binning_v}), value set to {node_binning_v.GetValue()}')
        else:
            print('Vertical binning node not available...')

    except PySpin.SpinnakerException as ex:
        print('set_binning() Error: %s' % ex)
        return(False)

    return(result)

## ====================================================================================
def get_image_width_height(nodemap, verbose=False):
    """
    Get the camera image dimensions.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    
    ## Initialize to all zero. If errors occur, then all-zeros indicates the error condition.
    image_width = 0
    image_height = 0
    
    try:
        ## Get the image width
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('WidthMax'))
        if PySpin.IsAvailable(node_width) and PySpin.IsReadable(node_width):
            image_width = node_width.GetValue()
            if verbose:
                print(f'Image width: {image_width}')
        else:
            print('Image width node not available...')

        ## Get the image height
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('HeightMax'))
        if PySpin.IsAvailable(node_height) and PySpin.IsReadable(node_height):
            image_height = node_height.GetValue()
            if verbose:
                print(f'Image height: {image_height}')
        else:
            print('Image height node not available...')
    except PySpin.SpinnakerException as ex:
        print('get_image_width_height() Error: %s' % ex)

    return(image_width, image_height)

## ====================================================================================
def set_autogain_off(nodemap, verbose=False):
    """
    This function temporarily disables automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    # Turn off automatic exposure mode
 
    try:
        result = True

        node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode('GainAuto'))
        if not PySpin.IsAvailable(node_gain_auto) or not PySpin.IsWritable(node_gain_auto):
            print('Autogain node not available...')
            return(False)

        gain_auto_off = node_gain_auto.GetEntryByName('Off')
        if not PySpin.IsAvailable(gain_auto_off) or not PySpin.IsReadable(gain_auto_off):
            print('Autogain_off node not available...')
            return(False)

        node_gain_auto.SetIntValue(gain_auto_off.GetValue())
        if verbose:
            print('Turning off auto-gain...')
    except PySpin.SpinnakerException as ex:
        print('set_autogain_off() Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def set_autogain_on(nodemap, verbose=False):
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode('GainAuto'))
        if not PySpin.IsAvailable(node_gain_auto) and PySpin.IsWritable(node_gain_auto):
            print('Autogain node not available...')
            return(False)

        gain_auto_continuous = node_gain_auto.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(gain_auto_continuous) and PySpin.IsReadable(gain_auto_continuous):
            print('Autogain_continuous node not available...')
            return(False)
       
        node_gain_auto.SetIntValue(gain_auto_continuous.GetValue())
        if verbose:
            print('Turning on auto-gain...')
    except PySpin.SpinnakerException as ex:
        print('set_autogain_on() Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def get_framerate(nodemap, verbose=False):
    """
    This function gets the current framerate setting (in Hz) of the camera.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
        if not PySpin.IsAvailable(node_acquisition_framerate) and not PySpin.IsReadable(node_acquisition_framerate):
            print('AcquisitionFrameRate node is not available...')
            return(0)

        current_framerate = node_acquisition_framerate.GetValue()
        if verbose:
            print(f'Current frame rate: {current_framerate:.1f} Hz')
    except PySpin.SpinnakerException as ex:
        print('get_framerate() Error: %s' % ex)
        current_framerate = 0

    return(current_framerate)

## ====================================================================================
def set_framerate(nodemap, new_framerate, verbose=False):
    """
    This function sets the framerate (in Hz) of the camera.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :param new_framerate: double
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True

        node_framerateenable = PySpin.CBooleanPtr(nodemap.GetNode('AcquisitionFrameRateEnable'))
        if not PySpin.IsAvailable(node_framerateenable) and not PySpin.IsReadable(node_framerateenable):
            print('AcquisitionFrameRateEnable node is not available...')
            return(False)

        node_acquisition_framerate = PySpin.CFloatPtr(nodemap.GetNode('AcquisitionFrameRate'))
        if not PySpin.IsAvailable(node_acquisition_framerate) and not PySpin.IsReadable(node_acquisition_framerate):
            print('AcquisitionFrameRate node is not available...')
            return(False)

        old_framerate = node_acquisition_framerate.SetValue(float(new_framerate))
        min_framerate = node_acquisition_framerate.GetMin()
        max_framerate = node_acquisition_framerate.GetMax()
        
        if (new_framerate > max_framerate):
            print('Cannot set the frame rate to {new_framerate:.1f} Hz, which is above the max allowed value of {max_framerate:.1f} Hz.')
            print('Defaulting to {max_framerate:.1f} Hz ...')
            new_framerate = max_framerate
        
        if (new_framerate < min_framerate):
            print('Cannot set the frame rate to {new_framerate:.1f} Hz, which is below the min allowed value of {min_framerate:.1f} Hz.')
            print('Defaulting to {min_framerate:.1f} Hz ...')
            new_framerate = min_framerate
        
        node_acquisition_framerate.SetValue(double(new_framerate))
        if verbose:
            print(f'Old frame rate = {old_framerate:.1f} Hz,   new frame rate: {new_framerate:.1f} Hz')
    except PySpin.SpinnakerException as ex:
        print('set_framerate() Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def acquire_num_images(cam, nodemap, num_images, do_filesave=False, verbose=False):
    """
    This function acquires and saves N images from a device.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    (image_width, image_height) = get_image_width_height(nodemap, verbose=False)

    try:
        ## Set acquisition mode to continuous.
        ## In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return(None, 0)

        ## Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return(None, 0)

        ## Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        ## Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        ## Begin acquiring images. Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        image_set = zeros((image_height,image_width,num_images), 'uint16')
        ts_set = zeros(num_images, 'uint64')
        
        ## Retrieve, convert, and save images
        for i in range(num_images):
            try:
                ## Retrieve the next received image. Capturing an image houses images on the camera buffer. Trying to
                ## capture an image that does not exist will hang the camera. Once an image from the buffer is saved
                ## and/or no longer needed, the image must be released in order to keep the buffer from filling up.
                image_result = cam.GetNextImage(1000)

                ## Ensure image completion. This should be done whenever a complete image is expected or required.
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
                    continue
                else:
                    ## Get the image height and width. Image objects have quite a bit of available metadata including
                    ## things such as CRC, image status, and offset values, to name a few.
                    #width = image_result.GetWidth()
                    #height = image_result.GetHeight()
                    #fmt = image_result.GetPixelFormatName()
                    ts_set[i] = image_result.GetTimeStamp()
                    #msg = 'Grabbed Image width=%d, height=%d, fmt=%s, timestamp(ns)=%d' % (width, height, fmt, ts)

                if do_filesave:
                    ## Convert image for saving. PySpin can save 16-bit data in RAW format, but all other formats must be 8-bit.
                    if filename.endswith('raw') and (image_result.GetPixelFormatName() == 'Mono16'):
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono16, PySpin.HQ_LINEAR)
                    else:
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                    filename = f'{i:05d}.tif'
                    image_converted.Save(filename)

                ## This is the numpy array result to return.
                image_set[:,:,i] = array(image_result.GetNDArray())
                #print(i, f'amin(image_set[:,:,i])={amin(image_set[:,:,i]):.1f}, amax(image_set[:,:,i])={amax(image_set[:,:,i]):.1f}')

                ## Release image. Images retrieved directly from the camera (i.e. non-converted
                ## images) need to be released in order to keep from filling the buffer.
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('acquire_num_images(): Error 1: %s' % ex)
                return(None, 0)

        ## End acquisition. Ending acquisition appropriately helps ensure that devices clean up
        ## properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()
    
    except PySpin.SpinnakerException as ex:
        print('acquire_num_images(): Error 2: %s' % ex)
        return(None, 0)

    return(image_set, ts_set)

## ====================================================================================
def acquire_one_image(cam, nodemap, filename='', verbose=False):
    """
    This function acquires and saves one image from a device.

    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :param nodemap: Device nodemap.
    :param filename: The filename to use if saving the image. Otherwise null string.
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    image_data = None

    try:
        ## Begin image acquisition. Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()
 
        ## Retrieve, convert, and save the image.
        try:
            ## Retrieve the next received image. Capturing an image houses images on the camera buffer. Trying to
            ## capture an image that does not exist will hang the camera. Once an image from the buffer is saved
            ## and/or no longer needed, the image must be released in order to keep the buffer from filling up.
            image_result = cam.GetNextImage(1000)

            ## Ensure image completion. This should be done whenever a complete image is expected or required.
            if image_result.IsIncomplete():
                print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
            else:
                ## Get the image height and width. Image objects have quite a bit of available metadata including
                ## things such as CRC, image status, and offset values, to name a few.
                #width = image_result.GetWidth()
                #height = image_result.GetHeight()
                #fmt = image_result.GetPixelFormatName()
                #msg = 'Grabbed Image width=%d, height=%d, fmt=%s, timestamp(ns)=%d' % (width, height, fmt, ts)

                if filename:
                    ## Convert image for saving. PySpin can save 16-bit data in RAW format, but all other formats must be 8-bit.
                    if filename.endswith('raw') and (image_result.GetPixelFormatName() == 'Mono16'):
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono16, PySpin.HQ_LINEAR)
                    else:
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                    image_converted.Save(filename)
                    if verbose:
                        print(msg + ', Image saved as: %s' % filename)
                elif verbose:
                    print(msg)

                ## This is the numpy array result to return. Flip up-down to fit bottom-left origin display.
                image_data = image_result.GetNDArray()
                ts = image_result.GetTimeStamp()
                
                ## Release image. Images retrieved directly from the camera (i.e. non-converted
                ## images) need to be released in order to keep from filling the buffer.
                image_result.Release()

        except PySpin.SpinnakerException as ex:
            print('acquire_one_image(): Error 1: %s' % ex)
            return(None, 0)

        ## End acquisition. Ending acquisition appropriately helps ensure that devices clean up
        ## properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()
    
    except PySpin.SpinnakerException as ex:
        print('acquire_one_image(): Error 2: %s' % ex)
        return(None, 0)

    return(image_data, ts)

## ====================================================================================
def video_fastsave(cam, nodemap, num_images, file_dir='', file_prefix='', file_suffix='raw', start_num=0, verbose=False):
    """
    This function acquires and saves N images, in RAW format, from a device.

    :param cam: Camera to acquire images from.
    :param nodemap: Device nodemap.
    :param nodemap_tldevice: Transport layer device nodemap.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    (image_width, image_height) = get_image_width_height(nodemap, verbose=False)

    try:
        ## Set acquisition mode to continuous.
        ## In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return(None, 0)

        ## Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return(None, 0)

        ## Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        ## Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        ## Begin acquiring images. Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()
        
        s = ''

        ## Retrieve, convert, and save images
        for i in range(num_images):
            filename = f'{file_dir}{file_prefix}_{start_num+i:05}.{file_suffix}'

            try:
                ## Retrieve the next received image. Capturing an image houses images on the camera buffer. Trying to
                ## capture an image that does not exist will hang the camera. Once an image from the buffer is saved
                ## and/or no longer needed, the image must be released in order to keep the buffer from filling up.
                image_result = cam.GetNextImage(1000)

                ## Ensure image completion. This should be done whenever a complete image is expected or required.
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
                    continue
                else:
                    if filename.endswith('raw') and (image_result.GetPixelFormatName() == 'Mono16'):
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono16, PySpin.HQ_LINEAR)
                    elif filename.endswith('tif') and (image_result.GetPixelFormatName() == 'Mono16'):
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono16, PySpin.HQ_LINEAR)
                    else:
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                    image_converted.Save(filename)
                   
                    if verbose:
                        s += f'Saved "{filename}": ts={image_result.GetTimeStamp()}\n'
                        #print(f'Saved "{filename}": ts={image_result.GetTimeStamp()}')

                ## Release image. Images retrieved directly from the camera (i.e. non-converted
                ## images) need to be released in order to keep from filling the buffer.
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('video_fastsave(): Error 1: %s' % ex)
                return(None, 0)

        ## End acquisition. Ending acquisition appropriately helps ensure that devices clean up
        ## properly and do not need to be power-cycled to maintain integrity.
        cam.EndAcquisition()
    
    except PySpin.SpinnakerException as ex:
        print('video_fastsave(): Error 2: %s' % ex)
        return(None, 0)

    return(s)

## ====================================================================================
def get_image_minmax(nodemap, verbose=False):
    """
    Retrieves the maximum width and height of the image.

    :param nodemap: Device GenICam nodemap
    :type nodemap: INodeMap
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    
    ## Initialize to all zero. If errors occur, then all-zeros indicates the error condition.
    min_width = 0
    max_width = 0
    min_height = 0
    max_height = 0

    try:
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
            min_width = node_width.GetMin()
            max_width = node_width.GetMax()
        else:
            print('Image width node not available...')

        ## Set image height
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
            min_height = node_height.GetMin()
            max_height = node_height.GetMax()
        else:
            print('Image height node not available...')
    except PySpin.SpinnakerException as ex:
        print('get_image_minmax(): Error: %s' % ex)

    return(min_width, max_width, min_height, max_height)

## ====================================================================================
def get_exposure_minmax(nodemap, verbose=False):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param nodemap: Device GenICam nodemap
     :type nodemap: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    ## Initialize to all zero. If errors occur, then all-zeros indicates the error condition.
    min_exposure_time = 0.0
    max_exposure_time = 0.0

    try:
        result = True

        node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode('ExposureTime'))
        if not PySpin.IsAvailable(node_exposure_time) and PySpin.IsReadable(node_exposure_time):
            print('ExposureTime node is not available.')
            return(0.0, 0.0)

        min_exposure_time = node_exposure_time.GetMin()
        max_exposure_time = node_exposure_time.GetMax()
    except PySpin.SpinnakerException as ex:
        print('get_exposure_minmax(): Error: %s' % ex)

    return(min_exposure_time, max_exposure_time)

## ====================================================================================
def get_exposure(nodemap, verbose=False):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param nodemap: Device GenICam nodemap
     :type nodemap: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    exposure_time = 0.0

    try:
        result = True

        node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode('ExposureTime'))
        if not PySpin.IsAvailable(node_exposure_time) and PySpin.IsReadable(node_exposure_time):
            print('ExposureTime node is not available.')
            return(0.0)

        exposure_time = node_exposure_time.GetValue()
    except PySpin.SpinnakerException as ex:
        print('get_exposure(): Error: %s' % ex)

    return(exposure_time)

## ====================================================================================
def set_exposure_compensation_off(nodemap, verbose=False):
    """
    This function temporarily disables automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
 
    try:
        result = True

        ## If exposure compensation function does not exist, you get a null pointer here. In that case, you don't need to
        ## turn it off!
        if not nodemap.GetNode('ExposureCompensationAuto'):
            return(True)

        node_exposure_compensation_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureCompensationAuto'))
        if not PySpin.IsAvailable(node_exposure_compensation_auto) and PySpin.IsWritable(node_exposure_compensation_auto):
            print('Autoexposure node is not available.')
            return(False)

        node_exposure_compensation_auto_off = node_exposure_compensation_auto.GetEntryByName("Off")
        if not PySpin.IsAvailable(node_exposure_compensation_auto_off) and PySpin.IsReadable(node_exposure_compensation_auto_off):
            print('Autoexposure_off node is not available.')
            return(False)
        
        node_exposure_compensation_auto.SetIntValue(node_exposure_compensation_auto_off.GetValue())
        if verbose:
            print('Turning auto exposure compensation off')
    except PySpin.SpinnakerException as ex:
        print('set_exposure_compensation_off(): Error: %s' % ex)
        result = False

    return(result)

## ====================================================================================
def set_exposure_compensation_on(nodemap, verbose=False):
    """
    This function temporarily disables automatic exposure.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
 
    try:
        result = True

        ## If exposure compensation function does not exist, you get a null pointer here. In that case, you don't need to
        ## turn it on!
        if not nodemap.GetNode('ExposureCompensationAuto'):
            return(True)

        node_exposure_compensation_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureCompensationAuto'))
        if not PySpin.IsAvailable(node_exposure_compensation_auto) and PySpin.IsWritable(node_exposure_compensation_auto):
            print('Autoexposure node is not available.')
            return(False)

        node_exposure_compensation_auto_on = node_exposure_compensation_auto.GetEntryByName("Continuous")
        if not PySpin.IsAvailable(node_exposure_compensation_auto_on) and PySpin.IsReadable(node_exposure_compensation_auto_on):
            print('Exposure_compensation_on node is not available.')
            return(False)
        
        node_exposure_compensation_auto.SetIntValue(node_exposure_compensation_auto_on.GetValue())
        if verbose:
            print('Turning auto exposure compensation on')
    except PySpin.SpinnakerException as ex:
        print('set_exposure_compensation_on(): Error: %s' % ex)
        result = False

    return result

## ====================================================================================
def save_image_pointer_list_to_avi(nodemap, image_list, avi_filename, image_height=480, image_width=640, avi_type='H264'):
    """
    This function writes an AVI video from a list of images.

    :param nodemap: Device nodemap.
    :param images: List of images to save to an AVI video.
    :type nodemap: INodeMap
    :type images: list of ImagePtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        result = True
        framerate = get_framerate(nodemap)
        avi_recorder = PySpin.SpinVideo()

        if (avi_type == 'UNCOMPRESSED'):
            option = PySpin.AVIOption()
            option.frameRate = framerate
        elif (avi_type == 'MJPG'):
            option = PySpin.MJPGOption()
            option.frameRate = framerate
            option.quality = 75
        elif (avi_type == 'H264'):
            option = PySpin.H264Option()
            option.frameRate = framerate
            option.bitrate = 1000000
            option.height = image_height
            option.width = image_width
        else:
            print('Error: Unknown AVI type. Aborting...')
            return(False)

        avi_recorder.Open(avi_filename, option)
        for i in range(len(image_list)):
            avi_recorder.Append(image_list[i])
            print('Appended image %d...' % i)

        avi_recorder.Close()
        print('Video saved at %s.avi' % avi_filename)

    except PySpin.SpinnakerException as ex:
        print('save_image_pointer_list_to_avi(): Error: %s' % ex)
        return(False)

    return(result)

## ====================================================================================
def get_gamma_enabled(nodemap, verbose=False):
    """
    This function returns whether the camera gamma value is enabled (True) or disabled (False).

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if enabled, False if disabled.
    :rtype: bool
    """

    try:
        node_gamma_enabled = PySpin.CBooleanPtr(nodemap.GetNode('GammaEnable'))
        if not PySpin.IsAvailable(node_gamma_enabled) and not PySpin.IsReadable(node_gamma_enabled):
            print('GammaEnable node is not available...')
            return(0)

        enabled = node_gamma_enabled.GetValue()
        if verbose:
            print(f'Gamma enabled value: {enabled}')
    except PySpin.SpinnakerException as ex:
        print('get_gamma_enabled(): Error: %s' % ex)
        enabled = None

    return(enabled)

## ====================================================================================
def enable_gamma(nodemap, verbose=False):
    """
    This function turns on the "gamma_enable" switch of the camera.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        node_gamma_enabled = PySpin.CBooleanPtr(nodemap.GetNode('GammaEnable'))
        if not PySpin.IsAvailable(node_gamma_enabled) and not PySpin.IsReadable(node_gamma_enabled):
            print('GammaEnable node is not available...')
            return(False)

        current_value = node_gamma_enabled.GetValue()
        if current_value:
            pass
        else:
            node_gamma_enabled.SetValue(True)
        
        if verbose:
            print(f'"Gamma_enabled" switch set to True')
    except PySpin.SpinnakerException as ex:
        print('enable_gamma(): Error: %s' % ex)
        return(False)

    return(True)

## ====================================================================================
def disable_gamma(nodemap, verbose=False):
    """
    This function turns off the "gamma_enable" switch of the camera.

    :param nodemap: Device GenICam nodemap
    :type nodemap: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    try:
        node_gamma_enabled = PySpin.CBooleanPtr(nodemap.GetNode('GammaEnable'))
        if not PySpin.IsAvailable(node_gamma_enabled) and not PySpin.IsReadable(node_gamma_enabled):
            print('GammaEnable node is not available...')
            return(False)

        current_value = node_gamma_enabled.GetValue()
        if not current_value:
            pass
        else:
            node_gamma_enabled.SetValue(False)
        
        if verbose:
            print(f'"Gamma_enabled" switch set to False')
    except PySpin.SpinnakerException as ex:
        print('disable_gamma(): Error: %s' % ex)
        return(False)

    return(True)

