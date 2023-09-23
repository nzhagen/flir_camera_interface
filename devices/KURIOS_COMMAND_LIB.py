from ctypes import *

import os, sys
this_folder = os.path.dirname(os.path.realpath(__file__))
os.add_dll_directory(this_folder)

#region import dll functions
KuriosLib = cdll.LoadLibrary("KURIOS_COMMAND_LIB_Win64.dll")

cmdOpen = KuriosLib.common_Open
cmdOpen.restype=c_int
cmdOpen.argtypes=[c_char_p, c_int, c_int]

cmdIsOpen = KuriosLib.common_IsOpen
cmdOpen.restype=c_int
cmdOpen.argtypes=[c_char_p]

cmdList = KuriosLib.common_List
cmdList.argtypes=[c_char_p]
cmdList.restype=c_int

cmdGetId = KuriosLib.kurios_Get_ID
cmdGetId.restype=c_int
cmdGetId.argtypes=[c_int, c_char_p]

cmdGetSpecification = KuriosLib.kurios_Get_Specification
cmdGetSpecification.restype=c_int
cmdGetSpecification.argtypes=[c_int, POINTER(c_int), POINTER(c_int)]

cmdGetOpticalHeadType = KuriosLib.kurios_Get_OpticalHeadType
cmdGetOpticalHeadType.restype= c_int
cmdGetOpticalHeadType.argtypes=[c_int, c_char_p, c_char_p]

cmdGetOutputMode = KuriosLib.kurios_Get_OutputMode
cmdGetOutputMode.restype=c_int
cmdGetOutputMode.argtypes=[c_int, POINTER(c_int)]

cmdSetOutputMode = KuriosLib.kurios_Set_OutputMode
cmdSetOutputMode.restype= c_int
cmdSetOutputMode.argtypes=[c_int, c_int]

cmdGetBandwidthMode = KuriosLib.kurios_Get_BandwidthMode
cmdGetBandwidthMode.restype=c_int
cmdGetBandwidthMode.argtypes=[c_int, POINTER(c_int)]

cmdSetBandwidthMode = KuriosLib.kurios_Set_BandwidthMode
cmdSetBandwidthMode.restype= c_int
cmdSetBandwidthMode.argtypes=[c_int, c_int]

cmdGetWavelength = KuriosLib.kurios_Get_Wavelength
cmdGetWavelength.restype=c_int
cmdGetWavelength.argtypes=[c_int, POINTER(c_int)]

cmdSetWavelength = KuriosLib.kurios_Set_Wavelength
cmdSetWavelength.restype= c_int
cmdSetWavelength.argtypes=[c_int, c_int]

cmdGetSequenceStepData = KuriosLib.kurios_Get_SequenceStepData
cmdGetSequenceStepData.restype=c_int
cmdGetSequenceStepData.argtypes=[c_int, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int)]

cmdSetSequenceStepData = KuriosLib.kurios_Set_SequenceStepData
cmdSetSequenceStepData.restype= c_int
cmdSetSequenceStepData.argtypes=[c_int, c_int, c_int, c_int, c_int]

cmdGetAllSequenceData = KuriosLib.kurios_Get_AllSequenceData
cmdGetAllSequenceData.restype=c_int
cmdGetAllSequenceData.argtypes=[c_int, c_char_p]

cmdSetInsertSequenceStep = KuriosLib.kurios_Set_InsertSequenceStep
cmdSetInsertSequenceStep.restype= c_int
cmdSetInsertSequenceStep.argtypes=[c_int, c_int, c_int, c_int, c_int, ]

cmdSetDeleteSequenceStep = KuriosLib.kurios_Set_DeleteSequenceStep
cmdSetDeleteSequenceStep.restype= c_int
cmdSetDeleteSequenceStep.argtypes=[c_int, c_int]

cmdSetDefaultWavelengthForSequence = KuriosLib.kurios_Set_DefaultWavelengthForSequence
cmdSetDefaultWavelengthForSequence.restype= c_int
cmdSetDefaultWavelengthForSequence.argtypes=[c_int, c_int]

cmdGetDefaultWavelengthForSequence = KuriosLib.kurios_Get_DefaultWavelengthForSequence
cmdGetDefaultWavelengthForSequence.restype= c_int
cmdGetDefaultWavelengthForSequence.argtypes=[c_int, POINTER(c_int)]

cmdSetDefaultBandwidthForSequence = KuriosLib.kurios_Set_DefaultBandwidthForSequence
cmdSetDefaultBandwidthForSequence.restype= c_int
cmdSetDefaultBandwidthForSequence.argtypes=[c_int, c_int]

cmdGetDefaultBandwidthForSequence = KuriosLib.kurios_Get_DefaultBandwidthForSequence
cmdGetDefaultBandwidthForSequence.restype=c_int
cmdGetDefaultBandwidthForSequence.argtypes=[c_int, POINTER(c_int)]

cmdSetDefaultTimeIntervalForSequence = KuriosLib.kurios_Set_DefaultTimeIntervalForSequence
cmdSetDefaultTimeIntervalForSequence.restype= c_int
cmdSetDefaultTimeIntervalForSequence.argtypes=[c_int, c_int]

cmdGetDefaultTimeIntervalForSequence = KuriosLib.kurios_Get_DefaultTimeIntervalForSequence
cmdGetDefaultTimeIntervalForSequence.restype=c_int
cmdGetDefaultTimeIntervalForSequence.argtypes=[c_int, POINTER(c_int)]

cmdGetSequenceLength = KuriosLib.kurios_Get_SequenceLength
cmdGetSequenceLength.restype=c_int
cmdGetSequenceLength.argtypes=[c_int, POINTER(c_int)]

cmdGetStatus = KuriosLib.kurios_Get_Status
cmdGetStatus.restype=c_int
cmdGetStatus.argtypes=[c_int, POINTER(c_int)]

cmdGetTemperature = KuriosLib.kurios_Get_Temperature
cmdGetTemperature.restype=c_int
cmdGetTemperature.argtypes=[c_int, POINTER(c_double)]

cmdSetTriggerOutSignalMode = KuriosLib.kurios_Set_TriggerOutSignalMode
cmdSetTriggerOutSignalMode.restype= c_int
cmdSetTriggerOutSignalMode.argtypes=[c_int, c_int]

cmdGetTriggerOutSignalMode = KuriosLib.kurios_Get_TriggerOutSignalMode
cmdGetTriggerOutSignalMode.restype=c_int
cmdGetTriggerOutSignalMode.argtypes=[c_int, POINTER(c_int)]

cmdSetForceTrigger = KuriosLib.kurios_Set_ForceTrigger
cmdSetForceTrigger.restype= c_int
cmdSetForceTrigger.argtypes=[c_int]

#endregion

#region command for Kurios
def KuriosListDevices():
    """ List all connected Kurios devices
    Returns: 
       The Kurios device list, each deice item is [serialNumber, descriptor]
    """
    str = create_string_buffer(1024, '\0')
    result = cmdList(str)
    devicesStr = str.raw.decode("utf-8").rstrip('\x00').split(',')
    length = len(devicesStr)
    i=0
    devices=[]
    devInfo=["",""]    
    while(i<length):
        str = devicesStr[i]
        if (i%2 == 0):
            if str != '':
                devInfo[0] = str
            else:
                i+=1
        else:      
            isFind = False
            if(str.find("KURIOS") >= 0):
                isFind = True;
            if(isFind):
                devInfo[1] = str
                devices.append(devInfo.copy())
        i+=1
    return devices

def KuriosOpen(serialNo, nBaud, timeout):
    """ Open Kurios device
    Args:
        serialNo: serial number of the device to be opened, use GetPorts function to get exist list first
        nBaud: bit per second of port
        timeout: set timeout value in (s)
    Returns: 
        non-negative number: hdl number returned Successful; negative number: failed.
    """
    return cmdOpen(serialNo.encode('utf-8'), nBaud, timeout)

def KuriosIsOpen(serialNo):
    """ Check opened status of Kurios device
    Args:
        serialNo: serial number of the device to be checked
    Returns: 
        0: device is not opened; 1: device is opened.
    """
    return cmdIsOpen(serialNo.encode('utf-8'))

def KuriosClose(hdl):
    """ Close opened Kurios device
    Args:
        hdl: the handle of opened device
    Returns: 
        0: Success; negative number: failed.
    """
    return KuriosLib.common_Close(hdl)

def KuriosGetId(hdl, id):
    """ Get the product header and firmware version
    Args:
        hdl: the handle of opened device
        id: the model number, hardware and firmware versions
    Returns: 
        0: Success; negative number: failed.
    """
    idStr = create_string_buffer(1024, '\0')
    ret = cmdGetId(hdl, idStr)
    id.append(idStr.raw.decode("utf-8").rstrip('\x00'))
    return ret

def KuriosGetSpecification(hdl, Max, Min):
    """ Get connected filter's wavelength range.
    Args:
        hdl: the handle of opened device
        Max: max wavelength
        Min: min wavelength
    Returns: 
        0: Success; negative number: failed.
    """
    Maximum = c_int(0)
    Minimum = c_int(0)
    ret = cmdGetSpecification(hdl, Maximum, Minimum)
    Max[0] = Maximum.value
    Min[0] = Minimum.value
    return ret

def KuriosGetOpticalHeadType(hdl, filterSpectrumRange, availableBandwidthMode):
    """ Get filter spectrum range and available bandwidth mode.
    Args:
        hdl: the handle of opened device
        filterSpectrumRange: 0000 0001 = Visible 
                             0000 0010 = NIR
                             0000 0100 = IR(future model)
        availableBandwidthMode: 0000 0001 = BLACK
                                0000 0010 = WIDE
                                0000 0100 = MEDIUM
                                0000 1000 = NARROW
                                0001 0000 = SUPER NARROW (future model)
    Returns: 
        0: Success; negative number: failed.
    """
    SpectrumRange = create_string_buffer(1024, '\0')
    BandwidthMode = create_string_buffer(1024, '\0') 
    ret = cmdGetOpticalHeadType(hdl, SpectrumRange, BandwidthMode)
    filterSpectrumRange.append(SpectrumRange.raw.decode("utf-8").rstrip('\x00'))
    availableBandwidthMode.append(BandwidthMode.raw.decode("utf-8").rstrip('\x00'))
    return ret

def KuriosSetOutputMode(hdl, value):
    """ Set output mode.
    Args:
        hdl: the handle of opened device
        value: 1 = manual (PC or front panel control) 
               2 = sequenced, internal clock triggered 
               3 = sequenced, external triggered 
               4 = analog signal controlled,  internal clock triggered 
               5 = analog signal controlled, external triggered
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetOutputMode(hdl, value)

def KuriosGetOutputMode(hdl, value):
    """ Get the current output mode.
    Args:
        hdl: the handle of opened device
        value: 1 = manual (PC or front panel control) 
               2 = sequenced, internal clock triggered 
               3 = sequenced, external triggered 
               4 = analog signal controlled,  internal clock triggered 
               5 = analog signal controlled, external triggered
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetOutputMode(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetBandwidthMode(hdl, value):
    """ Set the minimum output voltage limit for X axis.
    Args:
        hdl: the handle of opened device
        value: 1 = BLACK mode
               2 = WIDE mode
               4 = MEDIUM mode
               8 = NARROW mode
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetBandwidthMode(hdl, value)

def KuriosGetBandwidthMode(hdl, value):
    """ Get the maximum output voltage limit for X axis.
    Args:
        hdl: the handle of opened device
        value: 1 = BLACK mode
               2 = WIDE mode
               4 = MEDIUM mode
               8 = NARROW mode
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetBandwidthMode(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetWavelength(hdl, value):
    """ Set wavelength.
    Args:
        hdl: the handle of opened device
        value: wavelength within the available wavelength range
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetWavelength(hdl, value)

def KuriosGetWavelength(hdl, value):
    """ Get wavelength.
    Args:
         hdl: the handle of opened device
        value: wavelength within the available wavelength range
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetWavelength(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetSequenceStepData(hdl, Index, wavelength, interval, bandwidthMode):
    """ Set sequence step data.
    Args:
        hdl: the handle of opened device
        index: index
        wavelength: wavelength within filter range
        interval: time interval
        bandwidthMode: bandwidth mode
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetSequenceStepData(hdl, Index, wavelength, interval, bandwidthMode)

def KuriosGetSequenceStepData(hdl, Index, wavelength, interval, bandwidthMode):
    """ Get sequence step data.
    Args:
         hdl: the handle of opened device
         index: index
         wavelength: wavelength within filter range
         interval: time interval
         bandwidthMode: bandwidth mode
    Returns: 
        0: Success; negative number: failed.
    """
    Ind = c_int(0)
    wavele = c_int(0)
    inter = c_int(0)
    bandM = c_int(0)
    ret = cmdGetSequenceStepData(hdl, Ind, wavele, inter, bandM)
    wavelength[0] = wavele.value
    interval[0] =inter.value
    bandwidthMode[0] = bandM.value
    return ret 

def KuriosGetAllSequenceData(hdl, value):
    """ Get the entire sequence of wavelength and time interval.
    Args:
         hdl: the handle of opened device
        value: the entire sequence of wavelength and time interval
    Returns: 
        0: Success; negative number: failed.
    """
    val = create_string_buffer(1024, '\0')
    ret = cmdGetAllSequenceData(hdl, val)
    value.append(val.raw.decode("utf-8").rstrip('\x00'))
    return ret 

def KuriosSetInsertSequenceStep(hdl, index, wavelength, interval, bandwidthMode):
    """ Inserts an entry into the current sequence.
    Args:
         hdl: the handle of opened device
         index: index
         wavelength: wavelength within filter range
         interval: time interval
         bandwidthMode: bandwidth mode
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetInsertSequenceStep(hdl, index, wavelength, interval, bandwidthMode)

def KuriosSetDeleteSequenceStep(hdl, value):
    """ Deletes an entry from the current sequence.
    Args:
        hdl: the handle of opened device
        value: index of sequence step, 0 to delete all sequence
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetDeleteSequenceStep(hdl, value)

def KuriosSetDefaultWavelengthForSequence(hdl, value):
    """ Set default wavelength for sequence.
    Args:
        hdl: the handle of opened device
        value: wavelength within the available wavelength range
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetDefaultWavelengthForSequence(hdl, value)

def KuriosGetDefaultWavelengthForSequence(hdl, value):
    """ Get the current default wavelength for all elements in sequence.
    Args:
         hdl: the handle of opened device
        value: current default wavelength for all elements in sequence
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetDefaultWavelengthForSequence(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetDefaultBandwidthForSequence(hdl, value):
    """ Set bandwidth mode for all elements in sequence.
    Args:
        hdl: the handle of opened device
        value: 2 = WIDE mode
               4 = MEDIUM mode
               8 = NARROW mode
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetDefaultBandwidthForSequence(hdl, value)

def KuriosGetDefaultBandwidthForSequence(hdl, value):
    """ Get the current default Bandwidth Mode for all elements in sequence.
    Args:
        hdl: the handle of opened device
        value: 2 = WIDE mode
               4 = MEDIUM mode
               8 = NARROW mode
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetDefaultBandwidthForSequence(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetDefaultTimeIntervalForSequence(hdl, value):
    """ Set default time interval for sequence.
    Args:
        hdl: the handle of opened device
        value: internal trigger default time between 1ms and 60000ms
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetDefaultTimeIntervalForSequence(hdl, value)

def KuriosGetDefaultTimeIntervalForSequence(hdl, value):
    """ Get the current internal trigger default time.
    Args:
        hdl: the handle of opened device
        value: current internal trigger default time
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetDefaultTimeIntervalForSequence(hdl, val)
    value[0] = val.value
    return ret 

def KuriosGetSequenceLength(hdl, value):
    """ Get the sequence length.
    Args:
        hdl: the handle of opened device
        value: sequence length
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetSequenceLength(hdl, val)
    value[0] = val.value
    return ret

def KuriosGetStatus(hdl, value):
    """ Get the current filter status.
    Args:
        hdl: the handle of opened device
        value: 0 = initialization
               1 = warm up
               2 = ready
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetStatus(hdl, val)
    value[0] = val.value
    return ret

def KuriosGetTemperature(hdl, value):
    """ Get the current filter temperature.
    Args:
        hdl: the handle of opened device
        value: current filter temperature
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_double(0)
    ret = cmdGetTemperature(hdl, val)
    value[0] = val.value
    return ret

def KuriosSetTriggerOutSignalMode(hdl, value):
    """ Set trigger out signal mode.
    Args:
        hdl: the handle of opened device
        value: 0 = normal
               1 = flipped
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetTriggerOutSignalMode(hdl, value)

def KuriosGetTriggerOutSignalMode(hdl, value):
    """ Get trigger output mode setting.
    Args:
        hdl: the handle of opened device
        value:  0 = normal
                1 = flipped
    Returns: 
        0: Success; negative number: failed.
    """
    val = c_int(0)
    ret = cmdGetTriggerOutSignalMode(hdl, val)
    value[0] = val.value
    return ret 

def KuriosSetForceTrigger(hdl):
    """Enforce one step ahead in external triggered sequence mode (Firmware version 3.1 or above).
    Args:
        hdl: the handle of opened device
    Returns: 
        0: Success; negative number: failed.
    """
    return cmdSetForceTrigger(hdl)


#endregion


