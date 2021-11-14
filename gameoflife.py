from module import Module
import random
from datetime import datetime

class GameOfLife(Module):
    """Life"""

    def __init__(self, driver):
        if driver.width != 16 or driver.height != 16:
            raise Exception(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        random.seed(datetime.now())
        super().__init__(driver)

    def randomize():
        for x in range(self.width):
            for y in range(self.height):
                self.pixels[x][y] = 2 * random.random()
    


