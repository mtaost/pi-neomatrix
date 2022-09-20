import driver
from PIL import Image
from display_modes import module
import sys


class DisplayOff(module.Module):
    def __init__(self, driver):
        super().__init__(driver)
        self.image = Image.new('RGB', (self.width, self.height), 'black')
        self.pixels = self.image.load()

    def run(self):
        self.display()


if __name__ == "main":
    off = DisplayOff()
    off.run()
