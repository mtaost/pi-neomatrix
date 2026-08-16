import colorsys

from display_modes import module
from mode_settings import PIXEL_RAIN_SETTINGS, hex_to_rgb, normalize_settings
from numpy import linspace
import random
import logging

logger = logging.getLogger(__name__)

class PixelRain(module.Module):
    """Pixel rain, rainbow or other colors"""
    DELAY_MS = 40
    PERSISTENCE = 0.75  # Percent persistence of falling pixels per shift
    DENSITY = 30  # Number from 1 to 1000 indicating spawn rates at first layer
    MIN_BRIGHTNESS = 0.1
    RANDOM_COLOR_SELECTION = False

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.brightness_choices = linspace(self.MIN_BRIGHTNESS, 1.0, 20)
        self.rainbow_phase = 0.0
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(PIXEL_RAIN_SETTINGS, values, getattr(self, "settings", None))
        self.frame_delay = self.settings["frame_delay"]
        self.density = int(self.settings["density"])
        self.persistence = self.settings["persistence"]
        self.rain_color_mode = self.settings["rain_color_mode"]
        self.rain_fixed_color = hex_to_rgb(self.settings["rain_fixed_color"])
        self.rainbow_cycle_speed = self.settings["rainbow_cycle_speed"]
        self.rainbow_gradient_speed = self.settings["rainbow_gradient_speed"]
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

    # Shift all pixels down, with persistence of old pixels
    def _shift_down(self):
        for y in reversed(range(1, self.height)):
            for x in range(0, self.width):
                self.pixels[x, y] = self.pixels[x, y - 1]
                self.pixels[x, y - 1] = self._scale_brightness(self.pixels[x, y - 1], self.persistence)

    def _rainbow_color(self, hue):
        red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
        return tuple(round(channel * 255) for channel in (red, green, blue))

    def _spawn_color(self, x):
        if self.rain_color_mode == "fixed":
            return self.rain_fixed_color
        if self.rain_color_mode == "rainbow_cycle":
            return self._rainbow_color(self.rainbow_phase)
        return self._rainbow_color(self.rainbow_phase + x / self.width)

    # Place colors along top of matrix, selecting from color pallete and
    # based on DENSITY
    def _place_pixels(self):
        for x in range(0, self.width):
            if random.randint(0, 999) < self.density:
                brightness = random.choice(self.brightness_choices)
                self.pixels[x, 0] = self._scale_brightness(self._spawn_color(x), brightness)
        
    def _scale_brightness(self, color_tuple: tuple, brightness):
        return tuple(int(i * brightness) for i in color_tuple)

    def run(self):
        while not self.should_stop():
            self._place_pixels()
            self.display()
            self._shift_down()
            speed = self.rainbow_cycle_speed if self.rain_color_mode == "rainbow_cycle" else self.rainbow_gradient_speed
            self.rainbow_phase = (self.rainbow_phase + speed * self.frame_delay) % 1.0
            if not self.wait(self.frame_delay):
                break
