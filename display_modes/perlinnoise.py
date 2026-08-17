"""Animated Perlin-noise color gradients."""

import math

from display_modes import module
from mode_settings import PERLIN_NOISE_SETTINGS, hex_to_rgb, normalize_settings


class PerlinNoise(module.Module):
    """Render a smoothly animated, multi-layer Perlin-noise gradient."""

    PALETTES = {
        "aurora": ("#05001A", "#005B7F", "#00D084", "#B7FF5A"),
        "ocean": ("#001B44", "#005F73", "#0A9396", "#94D2BD"),
        "sunset": ("#14002E", "#6A0572", "#F72585", "#FFB703"),
        "ember": ("#090000", "#4A0000", "#D9381E", "#FFB000"),
        "neon": ("#10002B", "#3A0CA3", "#F72585", "#4CC9F0"),
    }

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.phase = 0.0
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(PERLIN_NOISE_SETTINGS, values, getattr(self, "settings", None))
        self.frame_delay = self.settings["frame_delay"]
        self.speed = self.settings["speed"]
        self.scale = self.settings["scale"]
        self.octaves = int(self.settings["octaves"])
        self.persistence = self.settings["persistence"]
        self.contrast = self.settings["contrast"]
        self.palette = self.settings["palette"]
        self.palette_colors = self._load_palette()
        return dict(self.settings)

    def _load_palette(self):
        if self.palette == "custom":
            values = (
                self.settings["custom_start_color"],
                self.settings["custom_mid_color"],
                self.settings["custom_end_color"],
            )
        else:
            values = self.PALETTES[self.palette]
        return tuple(hex_to_rgb(value) for value in values)

    @staticmethod
    def _hash01(x, y):
        value = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
        value ^= value >> 16
        return (value & 0xFFFFFFFF) / 0xFFFFFFFF

    @classmethod
    def _gradient(cls, x, y):
        angle = cls._hash01(x, y) * math.tau
        return math.cos(angle), math.sin(angle)

    @staticmethod
    def _fade(value):
        return value * value * value * (value * (value * 6 - 15) + 10)

    @classmethod
    def _perlin(cls, x, y):
        x0, y0 = math.floor(x), math.floor(y)
        dx, dy = x - x0, y - y0
        x1, y1 = x0 + 1, y0 + 1

        gradients = ((x0, y0, dx, dy), (x1, y0, dx - 1, dy), (x0, y1, dx, dy - 1), (x1, y1, dx - 1, dy - 1))
        dots = []
        for gx, gy, offset_x, offset_y in gradients:
            gradient_x, gradient_y = cls._gradient(gx, gy)
            dots.append(gradient_x * offset_x + gradient_y * offset_y)

        horizontal = cls._fade(dx)
        vertical = cls._fade(dy)
        top = dots[0] + horizontal * (dots[1] - dots[0])
        bottom = dots[2] + horizontal * (dots[3] - dots[2])
        return top + vertical * (bottom - top)

    def _noise_value(self, x, y):
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        amplitude_total = 0.0
        for _ in range(self.octaves):
            total += self._perlin(x * frequency, y * frequency) * amplitude
            amplitude_total += amplitude
            amplitude *= self.persistence
            frequency *= 2.0
        value = 0.5 + 0.5 * total / amplitude_total
        value = min(1.0, max(0.0, value))
        return min(1.0, max(0.0, 0.5 + (value - 0.5) * self.contrast))

    def _palette_color(self, value):
        position = value * (len(self.palette_colors) - 1)
        index = min(len(self.palette_colors) - 2, int(position))
        amount = position - index
        start = self.palette_colors[index]
        end = self.palette_colors[index + 1]
        return tuple(round(first + (second - first) * amount) for first, second in zip(start, end))

    def render_frame(self):
        drift_x = self.phase
        drift_y = self.phase * 0.63
        for x in range(self.width):
            for y in range(self.height):
                noise = self._noise_value(x * self.scale + drift_x, y * self.scale + drift_y)
                self.pixels[x, y] = self._palette_color(noise)

    def run(self):
        while not self.should_stop():
            self.render_frame()
            self.display()
            self.phase += self.speed * self.frame_delay
            if not self.wait(self.frame_delay):
                break
