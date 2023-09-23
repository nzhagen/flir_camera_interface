self.lctf_wavelist = arange(420,730,10)     ## returns a list from 420 to 720 in increments of 10
self.lctf_wave_counter = 0          ## counter for which element of wavelist is the current one
self.lctf_currentwave = self.lctf_wavelist[self.lctf_wave_counter]    ## the current wavelength

class kurios_lctf:
    pass

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

