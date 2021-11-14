import driver
from PIL import Image
import sys

class Module:
    """Base class of modules for pixel displays"""

    STOP = False

    def __init__(self, driver):
        self.width = driver.width
        self.height = driver.height
        self.driver = driver
        self.image = Image.new('RGB', (self.width,self.height), 'black')
        self.pixels = self.image.load()

    def display(self):
        if Module.STOP:
            self.cleanup()
        self.driver.display(self.image)

    def run(self):
        while 1:
            pass

    def cleanup(self):
        sys.exit(1)


