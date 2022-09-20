import driver
from PIL import Image
from display_modes import module
from numpy import linspace
from datetime import datetime
from time import sleep, time
import random

class PixelRain(module.Module):
    """Pixel rain, rainbow or other colors"""
    DELAY_MS = 50
    PERSISTENCE = 0.75 # Percent persistence of falling pixels per shift
    DENSITY = 100 # Number from 1 to 1000 indicating spawn rates at first layer
    MIN_BRIGHTNESS = 0.01
    RANDOM_COLOR_SELECTION = False

    def __init__(self, driver):
        super().__init__(driver)
        self.color_pallete = self._generate_rainbow_colors(1000)
        self.brightness_choices = linspace(self.MIN_BRIGHTNESS, 1.0, 20)
        random.seed(datetime.now())
        self.color_index = 0

    # Generates rainbow colors with n increments between each color transition
    def _generate_rainbow_colors(self, n):
        color_list = []
        increments = [int(i) for i in linspace(0, 255, n)]
        # Full red, increasing green
        for j in range(n):
            color_list.append((255, increments[j], 0))
        color_list.pop()
        # Full green, decreasing red
        for j in range(n):
            color_list.append((increments[-1 - j], 255, 0))
        color_list.pop()
        # Full green, increasing blue
        for j in range(n):
            color_list.append((0, 255, increments[j]))
        color_list.pop()
        # Full blue, decreasing green
        for j in range(n):
            color_list.append((0, increments[-1 - j], 255))
        color_list.pop()
        # Full blue, increasing red
        for j in range(n):
            color_list.append((increments[j], 0, 255))
        color_list.pop()
        # Full red, decreasing blue
        for j in range(n):
            color_list.append((255, 0, increments[-1 - j]))
        color_list.pop()
        return color_list

    # Shift all pixels down, with persistence of old pixels
    def _shift_down(self):
        for y in reversed(range(1, self.height)):
            for x in range(0, self.width):
                self.pixels[x, y] = self.pixels[x, y - 1]
                self.pixels[x, y - 1] = self._scale_brightness(self.pixels[x, y - 1], self.PERSISTENCE)

    # Place colors along top of matrix, selecting from color pallete and
    # based on DENSITY
    def _place_pixels(self):
        for x in range(0, self.width):
            if random.randint(0, 999) < self.DENSITY:
                brightness = random.choice(self.brightness_choices)
                if self.RANDOM_COLOR_SELECTION:
                    self.pixels[x, 0] = self._scale_brightness(random.choice(self.color_pallete), brightness)
                
                else:
                    self.pixels[x, 0] = self._scale_brightness(self.color_pallete[self.color_index], brightness)
                    self.color_index += 1
                    if self.color_index == len(self.color_pallete):
                        self.color_index = 0
        
    def _scale_brightness(self, color_tuple: tuple, brightness ):
        return tuple(int(i * brightness) for i in color_tuple)

    def run(self):
        while 1:
            start = time()
            self._place_pixels()
            self.display()
            self._shift_down()
            sleep(self.DELAY_MS/1000)
            # print(f"FPS: {1/(time() - start):.1f}")
