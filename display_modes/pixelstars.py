import driver
from PIL import Image
from display_modes import module
from numpy import linspace
from datetime import datetime
from time import sleep, time
import random
import colorlog

logger = colorlog.getLogger(__name__)


class PixelStars(module.Module):
    """ Pixel stars, fading over time"""
    DELAY_MS = 30
    PERSISTENCE = 0.99  # Percent persistence of pixels each frame
    DENSITY = 5  # Number from 1 to 100000 indicating spawn rates
    DENSITY_BURST_CHANCE = 1  # Number from 1 to 10000 indicating density burst chance
    DENSITY_BURST_MAX = 90  # Density burst number
    MIN_BRIGHTNESS = .1
    RANDOM_COLOR_SELECTION = False

    def __init__(self, driver):
        super().__init__(driver)
        self.color_pallete = self._generate_rainbow_colors(100)
        # self.color_pallete = [(255, 255, 255), (255, 255, 255)]
        self.brightness_choices = linspace(self.MIN_BRIGHTNESS, 1.0, 20)
        random.seed(datetime.now())
        self.color_index = 0
        self.curr_density = self.DENSITY
        # self.pixel_index = 0
        # self.going_right = True

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

    # Dim all pixels on the board
    def _dim_pixels(self):
        for y in range(self.height):
            for x in range(0, self.width):
                if self.pixels[x, y] != (0, 0, 0):
                    self.pixels[x, y] = self._scale_brightness(self.pixels[x, y], self.PERSISTENCE)

    # Place colors along top of matrix, selecting from color pallete and
    # based on DENSITY
    def _place_pixels(self):
        for x in range(self.width):
            for y in range(self.height):
                if random.randint(0, 99999) < self.curr_density:
                    brightness = random.choice(self.brightness_choices)
                    if self.RANDOM_COLOR_SELECTION:
                        self.pixels[x, y] = self._scale_brightness(random.choice(self.color_pallete), brightness)
                    
                    else:
                        self.pixels[x, y] = self._scale_brightness(self.color_pallete[self.color_index], brightness)
                        self.color_index += 1
                        if self.color_index == len(self.color_pallete):
                            self.color_index = 0
        
    def _scale_brightness(self, color_tuple: tuple, brightness):
        return tuple(int(i * brightness) for i in color_tuple)

    def _reroll_density(self):
        """ Temporarily raise current density if lucky """
        if self.curr_density == self.DENSITY:
            if random.randint(0, 9999) < self.DENSITY_BURST_CHANCE:
                self.curr_density = self.DENSITY_BURST_MAX

        else:
            self.curr_density -= 1

    def run(self):
        while True:
            start = time()
            self._place_pixels()
            self.display()
            self._dim_pixels()
            self._reroll_density()
            sleep(self.DELAY_MS/1000)
            # logger.info(f"FPS: {1/(time() - start):.1f}")
