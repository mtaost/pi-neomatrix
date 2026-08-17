"""A warm, animated fireplace with flickering flames and rising embers."""

import math
import random

from display_modes import module
from display_modes.perlinnoise import PerlinNoise
from mode_settings import FIREPLACE_SETTINGS, hex_to_rgb, normalize_settings


PALETTES = {
    "classic": ("#120000", "#B51A05", "#FF6A00", "#FFF2A1"),
    "hearth": ("#160000", "#8C1200", "#F04A00", "#FFD166"),
    "candle": ("#1A0800", "#D35400", "#FFB000", "#FFF8D6"),
    "blue_flame": ("#00051A", "#003C78", "#00A6D6", "#B6F4FF"),
    "neon": ("#18002E", "#B00070", "#FF3D71", "#FFD166"),
}


class Fireplace(module.Module):
    """Render a compact, continuously flickering fireplace scene."""

    LOG_DARK = (45, 16, 8)
    LOG_LIGHT = (105, 39, 13)

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.phase = 0.0
        self.embers = []
        self.random = random.Random()
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(FIREPLACE_SETTINGS, values, getattr(self, "settings", None))
        self.frame_delay = self.settings["frame_delay"]
        self.flame_height = self.settings["flame_height"]
        self.flame_scale = self.settings["flame_scale"]
        self.flicker = self.settings["flicker"]
        self.turbulence = self.settings["turbulence"]
        self.ember_density = self.settings["ember_density"]
        self.palette_name = self.settings["palette"]
        self.palette = self._load_palette()
        return dict(self.settings)

    def _load_palette(self):
        if self.palette_name == "custom":
            values = (
                self.settings["custom_shadow_color"],
                self.settings["custom_mid_color"],
                self.settings["custom_highlight_color"],
            )
        else:
            values = PALETTES[self.palette_name]
        return tuple(hex_to_rgb(value) for value in values)

    def _noise(self, x, y):
        """Return smooth noise in the 0..1 range with optional fine detail."""
        coarse = PerlinNoise._perlin(x, y)
        fine = PerlinNoise._perlin(x * 2.4 + 17.0, y * 2.4 - 11.0)
        value = coarse * (1.0 - self.turbulence) + fine * self.turbulence
        return min(1.0, max(0.0, 0.5 + value))

    def _palette_color(self, value):
        position = min(1.0, max(0.0, value)) * (len(self.palette) - 1)
        index = min(len(self.palette) - 2, int(position))
        amount = position - index
        start, end = self.palette[index], self.palette[index + 1]
        return tuple(round(first + (second - first) * amount) for first, second in zip(start, end))

    def _draw_logs(self):
        if self.height < 2:
            return
        for x in range(self.width):
            self.pixels[x, self.height - 1] = self.LOG_DARK
            self.pixels[x, self.height - 2] = self.LOG_LIGHT if x % 3 else self.LOG_DARK
        if self.width >= 6:
            for x in range(2, self.width - 2):
                self.pixels[x, self.height - 2] = self.LOG_LIGHT

    def _draw_flames(self):
        usable_height = max(1, self.height - 3)
        for x in range(self.width):
            for y in range(usable_height):
                from_bottom = (usable_height - 1 - y) / max(1, usable_height - 1)
                relative_height = from_bottom / self.flame_height
                if relative_height > 1.0:
                    continue

                sample_x = (x - self.width / 2) * self.flame_scale + self.phase
                sample_y = relative_height * 2.2 - self.phase * 0.7
                noise = self._noise(sample_x, sample_y)
                width_factor = 1.0 - relative_height * 0.72
                edge = noise - (1.0 - width_factor) * 0.55 - 0.24
                if edge <= 0:
                    glow = (1.0 - relative_height) * (1.0 - noise) * 0.12
                    if glow > 0.02:
                        self.pixels[x, y] = self._palette_color(glow)
                    continue

                heat = (1.0 - relative_height) ** 0.45
                heat *= min(1.0, edge * (1.8 + self.flicker * 1.8))
                self.pixels[x, y] = self._palette_color(heat)

    def _spawn_embers(self):
        chance = self.ember_density / 100.0 * self.frame_delay * 2.0
        if self.random.random() >= chance:
            return
        life = self.random.randint(7, 16)
        self.embers.append({
            "x": self.random.uniform(1, max(1, self.width - 2)),
            "y": float(max(0, self.height - 3)),
            "vx": self.random.uniform(-0.12, 0.12),
            "vy": self.random.uniform(-0.35, -0.12),
            "life": life,
            "max_life": life,
        })

    def _update_embers(self):
        self._spawn_embers()
        remaining = []
        for ember in self.embers:
            ember["x"] += ember["vx"]
            ember["y"] += ember["vy"]
            ember["vy"] += 0.012
            ember["life"] -= 1
            x, y = round(ember["x"]), round(ember["y"])
            if ember["life"] > 0 and 0 <= x < self.width and 0 <= y < self.height - 2:
                brightness = ember["life"] / ember["max_life"]
                self.pixels[x, y] = self._palette_color(0.75 + 0.25 * brightness)
                remaining.append(ember)
        self.embers = remaining

    def step(self):
        self.image.paste((0, 0, 0), (0, 0, self.width, self.height))
        self._draw_flames()
        self._draw_logs()
        self._update_embers()
        self.phase += self.frame_delay * (0.35 + self.flicker * 1.65)

    def run(self):
        while not self.should_stop():
            self.step()
            self.display()
            if not self.wait(self.frame_delay):
                break
