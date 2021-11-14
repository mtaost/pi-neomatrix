import driver
from PIL import Image

class Module:
    """Base class of modules for pixel displays"""

    def __init__(self, driver):
        self.width = driver.width
        self.height = driver.height
        self.driver = driver
        self.image = Image.new('RGB', (self.width,self.height), 'black')
        self.pixels = self.image.load()

    def display(self, arr):
        self.driver.display(arr)


