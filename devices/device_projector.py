import numpy
import slmpy

class fpp_projector:
    ## ===================================
    def __init__(self):
        ## Create the object that handles the SLM array.
        ## By default, "slmpy" uses the second display (i.e. monitor=1) for displaying images. If you have more
        ## than one monitor/projector/SLM, you may want to specify which monitor is the monitor/projector/SLM.
        ## The "isImageLock=True" variable means that the program will wait until the new image display is completed
        ## before continuing to the next step in the code (in case you are operating in a fast loop).
        self.proj = slmpy.SLMdisplay(monitor=1, isImageLock=True)

        ## Ask for the pixel dimensions of the monitor/projector/SLM display.
        (self.Ny,self.Nx) = self.proj.getSize()

        ## Make a set of coordinates for generating the fringe patterns for projection.
        (self.proj_xcoord,self.proj_ycoord) = numpy.indices((self.Nx,self.Ny))

        return

    ## ===================================
    def project_pattern(self, pattern_image):
        ## Send an image to the monitor/projector/SLM.
        self.proj.updateArray(pattern_image)

        return

