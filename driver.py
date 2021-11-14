import board
import neopixel
import numpy as np
import time
from timeit import timeit
from PIL import Image
from functools import reduce 
from operator import mul

def generate_map():
    """ Returns a mapping array to translate a x and y coordinate into an index"""
    A = np.reshape([list(range(64))], (8,8))
    B = np.reshape([list(range(64, 128))], (8,8))
    C = np.reshape([list(range(128, 192))], (8,8))
    D = np.reshape([list(range(192, 256))], (8,8))
    AB = np.concatenate((A, B), 0)
    CD = np.concatenate((C, D), 0)
    result = np.concatenate((AB, CD), 1)
    return result

class MatrixDriver():
    """ MatrixDriver is an abstraction for the Adafruit Neopixel library 
        Provides modules a width by height 3-tuple input to drive a matrix"""

    """ Change parameters here to adjust for your setup"""
    def __init__(self, 
        pin = board.D12,
        width = 16, 
        height = 16,
        order = neopixel.GRB
        ):
        
        self.pin = pin
        self.width = width
        self.height = height
        self.order = order
        self.index_map = generate_map()
        # self.index_map = np.rot90(self.index_map, 2)

        self.__brightness__ = 0.25
        self.pixels = neopixel.NeoPixel(pin, width * height, auto_write=False, pixel_order=order)

    def display(self, img):
        """ Accepts a 3d numpy array with the 3rd dimension being R G B """

        # Take pixel data, convert to list of tuples, then reshape that list into a 2d list of tuples
        # This is done so the pixels can be remapped arbitrarily 
        pixel_data = list(tuple(pixel) for pixel in img.getdata())
        pixel_data_matrix = self.__reshape__(pixel_data, (self.width, self.height))
        for x in range(self.width):
            for y in range(self.height):
                index = self.index_map[x, y]
                self.pixels[index] = (self.__scale_brightness__((pixel_data_matrix[x][y])))

        self.pixels.show()

    def set_brightness(self, b: int):
        """ Sets brightness of entire display from 0.0 to 1.0 """
        if (b > 1.0):
            b = 1.0
        elif (b < 0.0):
            b = 0.0
        self.__brightness__ = b

    def __scale_brightness__(self, color_tuple: tuple):
        return tuple(int(i * self.__brightness__) for i in color_tuple)

    def __reshape__(self, lst, shape):
        if len(shape) == 1:
            return lst
        n = reduce(mul, shape[1:])
        return [self.__reshape__(lst[i*n:(i+1)*n], shape[1:]) for i in range(len(lst)//n)]

    def stop(self):
        self.pixels.deinit()

if __name__ == "__main__":

    img = Image.new('RGB', (16,16), "green")

    matrix_driver = MatrixDriver()
    
    start_time = time.time()
    pixels = img.load()
    print(pixels)
    for x in range(16):
        for y in range(16):
            pixels[x, y]=(0, 0, 0)
            matrix_driver.display(img)
    stop_time = time.time()
    print(f"Total time: {stop_time - start_time}")