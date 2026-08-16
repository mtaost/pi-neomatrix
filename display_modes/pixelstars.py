import colorsys

from display_modes import module
from mode_settings import PIXEL_STARS_SETTINGS, hex_to_rgb, normalize_settings
from numpy import linspace
import random
import logging

logger = logging.getLogger(__name__)


class PixelStars(module.Module):
    """ Pixel stars, fading over time"""
    DELAY_MS = 30
    PERSISTENCE = 0.99  # Percent persistence of pixels each frame
    DENSITY = 5  # Number from 1 to 100000 indicating spawn rates
    DENSITY_BURST_CHANCE = 1  # Number from 1 to 10000 indicating density burst chance
    DENSITY_BURST_MAX = 90  # Density burst number
    MIN_BRIGHTNESS = .1
    RANDOM_COLOR_SELECTION = False

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.brightness_choices = linspace(self.MIN_BRIGHTNESS, 1.0, 20)
        self.rainbow_phase = 0.0
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(PIXEL_STARS_SETTINGS, values, getattr(self, "settings", None))
        self.frame_delay = self.settings["frame_delay"]
        self.density = int(self.settings["density"])
        self.persistence = self.settings["persistence"]
        self.burst_chance = int(self.settings["burst_chance"])
        self.burst_density = max(self.density, int(self.settings["burst_density"]))
        self.star_color_mode = self.settings["star_color_mode"]
        self.star_fixed_color = hex_to_rgb(self.settings["star_fixed_color"])
        self.rainbow_cycle_speed = self.settings["rainbow_cycle_speed"]
        self.rainbow_gradient_speed = self.settings["rainbow_gradient_speed"]
        self.curr_density = self.density
        return dict(self.settings)

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
                    self.pixels[x, y] = self._scale_brightness(self.pixels[x, y], self.persistence)

    # Place colors along top of matrix, selecting from color pallete and
    def _rainbow_color(self, hue):
        red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
        return tuple(round(channel * 255) for channel in (red, green, blue))

    def _spawn_color(self, x, y):
        if self.star_color_mode == "fixed":
            return self.star_fixed_color
        if self.star_color_mode == "rainbow_cycle":
            return self._rainbow_color(self.rainbow_phase)
        gradient = (x / self.width + y / self.height) / 2
        return self._rainbow_color(self.rainbow_phase + gradient)

    # based on DENSITY
    def _place_pixels(self):
        for x in range(self.width):
            for y in range(self.height):
                if random.randint(0, 99999) < self.curr_density:
                    brightness = random.choice(self.brightness_choices)
                    self.pixels[x, y] = self._scale_brightness(self._spawn_color(x, y), brightness)
        
    def _scale_brightness(self, color_tuple: tuple, brightness):
        return tuple(int(i * brightness) for i in color_tuple)

    def _reroll_density(self):
        """ Temporarily raise current density if lucky """
        if self.curr_density == self.density:
            if random.randint(0, 9999) < self.burst_chance:
                self.curr_density = self.burst_density
        else:
            self.curr_density = max(self.density, self.curr_density - 1)

    def run(self):
        while not self.should_stop():
            self._place_pixels()
            self.display()
            self._dim_pixels()
            self._reroll_density()
            speed = self.rainbow_cycle_speed if self.star_color_mode == "rainbow_cycle" else self.rainbow_gradient_speed
            self.rainbow_phase = (self.rainbow_phase + speed * self.frame_delay) % 1.0
            if not self.wait(self.frame_delay):
                break
