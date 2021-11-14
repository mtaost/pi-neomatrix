import board
import neopixel
import numpy as np
import time
from timeit import timeit
from PIL import Image

def generate_map():
    """ Returns a mapping array to translate a x and y coordinate into an index"""
    A = np.reshape([list(range(64))], (8,8))
    B = np.reshape([list(range(64, 128))], (8,8))
    C = np.reshape([list(range(128, 192))], (8,8))
    D = np.reshape([list(range(192, 256))], (8,8))
    AB = np.concatenate((A, B), 0)
    CD = np.concatenate((C, D), 0)
    ABCD = np.concatenate((AB, CD), 1)
    # ABCD = np.rot90(ABCD, 1)
    result = np.flip(ABCD, (1))
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

        self.__brightness__ = 0.25
        self.pixels = neopixel.NeoPixel(pin, width * height, auto_write=False, pixel_order=order)

    def display(self, img):
        """ Accepts a 3d numpy array with the 3rd dimension being R G B """

        # Take pixel data, convert to list of tuples, then reshape that list into a 2d list of tuples
        # This is done so the pixels can be remapped arbitrarily 
        # pixel_data = list(tuple(pixel) for pixel in img.getdata())
        # pixel_data_matrix = self.__reshape__(pixel_data, (self.width, self.height))
        pixel_data_matrix = img.load()
        #       self.pixels[index] = (self.__scale_brightness__((pixel_data_matrix[x, y])))
        for x in range(self.width):
            for y in range(self.height):
                index = self.index_map[x, y]
                self.pixels[index] = (self.__scale_brightness__((pixel_data_matrix[x, y])))

        self.pixels.show()

    def clear(self, img):
        pixel_data = img.load()
        for x in range(img.size[0]):
            for y in range(img.size[1]):
                pixel_data[x, y] = (0, 0, 0)

    def set_brightness(self, b: int):
        """ Sets brightness of entire display from 0.0 to 1.0 """
        if (b > 1.0):
            b = 1.0
        elif (b < 0.0):
            b = 0.0
        self.__brightness__ = b

    def __scale_brightness__(self, color_tuple: tuple):
        return tuple(int(i * self.__brightness__) for i in color_tuple)

    def stop(self):
        self.pixels.deinit()

if __name__ == "__main__":

    # img = Image.new('RGB', (16,16), "green")
    matrix_driver = MatrixDriver()
    matrix_driver.set_brightness(0.10)
    # with Image.open("ifabpartners.png") as img:
    #     # pixels = im.load()
    # # start_time = time.time()
    #     img = img.convert('RGB')
    #     matrix_driver.display(img)
    

    with Image.open("shrek.gif") as img:
        # img.seek(1000) # skip to the second frame
        frame = 1000
        while 1:
            frame += 1
            # for frame in range (img.n_frames):
            img.seek(frame)
            rgb_img = img.convert('RGB')
            resized = rgb_img.resize((16,16))
            matrix_driver.display(resized)
            time.sleep(0.065)
    time.sleep(15)

    pixels = img.load()
    # for x in range(16):
    #     for y in range(16):
    #         # print(pixels[x,y])
    #         pixels[x, y]=(0, 0, 0)
    #         matrix_driver.display(img)
    # stop_time = time.time()
    # print(f"Total time: {stop_time - start_time}")