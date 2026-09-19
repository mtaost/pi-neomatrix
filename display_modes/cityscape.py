"""An endlessly scrolling, pixel-art city skyline."""

import math
import time

from display_modes import module
from mode_settings import CITYSCAPE_SETTINGS, normalize_settings


class Cityscape(module.Module):
    """Render a procedurally generated city against a changing sky.

    Buildings are addressed by world coordinates rather than stored in a
    finite canvas.  As the offset grows, new deterministic blocks are drawn
    at the right edge, making the skyline effectively infinite without a
    growing memory cost.
    """

    SKIES = {
        "day": ((78, 171, 235), (218, 242, 255)),
        "sunset": ((91, 20, 93), (255, 141, 74)),
        "night": ((2, 5, 27), (15, 37, 83)),
    }

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.scroll_offset = 0.0
        self.cycle_elapsed = 0.0
        self._last_step_at = None
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(
            CITYSCAPE_SETTINGS, values, getattr(self, "settings", None)
        )
        self.frame_delay = self.settings["frame_delay"]
        self.scroll_speed = self.settings["scroll_speed"]
        self.sky_mode = self.settings["sky_mode"]
        self.cycle_duration = self.settings["cycle_duration"]
        self.building_height = self.settings["building_height"]
        self.window_density = self.settings["window_density"] / 100.0
        return dict(self.settings)

    @staticmethod
    def _blend(first, second, amount):
        amount = min(1.0, max(0.0, amount))
        return tuple(round(a + (b - a) * amount) for a, b in zip(first, second))

    @staticmethod
    def _hash01(x, y=0, salt=0):
        """Return stable pseudo-random noise for positive and negative cells."""
        value = (x * 374761393 + y * 668265263 + salt * 1442695041) & 0xFFFFFFFF
        value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
        value ^= value >> 16
        return (value & 0xFFFFFFFF) / 0xFFFFFFFF

    def _sky(self):
        """Return gradient colors and light levels for the selected sky mode."""
        if self.sky_mode != "cycle":
            top, bottom = self.SKIES[self.sky_mode]
            return top, bottom, 1.0 if self.sky_mode == "night" else 0.18 if self.sky_mode == "sunset" else 0.0, 1.0 if self.sky_mode == "sunset" else 0.0

        phase = (self.cycle_elapsed / self.cycle_duration) % 1.0
        # Night, dawn, day, sunset, and dusk occupy a full seamless loop.
        if phase < 0.23:
            first, second, amount, nightness, sunsetness = "night", "night", 0.0, 1.0, 0.0
        elif phase < 0.34:
            amount = (phase - 0.23) / 0.11
            first, second, nightness, sunsetness = "night", "day", 1.0 - amount, 0.0
        elif phase < 0.64:
            first, second, amount, nightness, sunsetness = "day", "day", 0.0, 0.0, 0.0
        elif phase < 0.74:
            amount = (phase - 0.64) / 0.10
            first, second, nightness, sunsetness = "day", "sunset", amount * 0.18, amount
        elif phase < 0.85:
            first, second, amount, nightness, sunsetness = "sunset", "sunset", 0.0, 0.18, 1.0
        else:
            amount = (phase - 0.85) / 0.15
            first, second, nightness, sunsetness = "sunset", "night", 0.18 + amount * 0.82, 1.0 - amount
        top = self._blend(self.SKIES[first][0], self.SKIES[second][0], amount)
        bottom = self._blend(self.SKIES[first][1], self.SKIES[second][1], amount)
        return top, bottom, nightness, sunsetness

    def _draw_sky(self, top, bottom, nightness):
        horizon = max(1, self.height - 1)
        for y in range(self.height):
            color = self._blend(top, bottom, y / horizon)
            for x in range(self.width):
                self.pixels[x, y] = color

                # Star positions are fixed in sky-world space, so they drift
                # slowly with the distant skyline instead of flickering.
                world_x = math.floor(x + self.scroll_offset * 0.18)
                if y < self.height * 0.58 and self._hash01(world_x, y, 71) < 0.045 * nightness:
                    self.pixels[x, y] = self._blend(color, (205, 222, 255), 0.75 * nightness)

    def _draw_celestial_body(self, nightness, sunsetness):
        ground = self.height - 1
        if ground < 2:
            return
        if nightness > 0.62:
            center_x = max(1, self.width * 3 // 4)
            center_y = max(1, ground // 4)
            color = (198, 215, 255)
        else:
            center_x = max(1, self.width * 2 // 3)
            center_y = max(1, round(ground * (0.20 + 0.48 * sunsetness)))
            color = self._blend((255, 248, 187), (255, 197, 79), sunsetness)
        for x, y in ((center_x, center_y), (center_x - 1, center_y), (center_x + 1, center_y), (center_x, center_y - 1), (center_x, center_y + 1)):
            if 0 <= x < self.width and 0 <= y < ground:
                self.pixels[x, y] = color

    def _building(self, world_x, layer):
        """Return ``(height, has_building)`` for one procedural city column."""
        block_width = 6 if layer == "distant" else 5
        block, column = divmod(world_x, block_width)
        seed = self._hash01(block, salt=13 if layer == "distant" else 29)
        start = 1 if self._hash01(block, salt=31) > 0.58 else 0
        width = 2 + int(seed * (2 if layer == "distant" else 3))
        if not start <= column < min(block_width, start + width):
            return 0, False
        if layer == "distant":
            maximum = max(2, round(self.height * self.building_height * 0.52))
            return 1 + int(self._hash01(block, salt=47) * maximum), True
        maximum = max(3, round(self.height * self.building_height))
        return 2 + int(self._hash01(block, salt=53) * max(1, maximum - 1)), True

    def _draw_buildings(self, nightness):
        ground = self.height - 1
        distant_color = self._blend((43, 70, 100), (5, 9, 29), nightness)
        near_color = self._blend((31, 43, 62), (3, 5, 15), nightness)
        window_color = self._blend((255, 219, 132), (255, 179, 63), nightness)

        for x in range(self.width):
            world_x = math.floor(x + self.scroll_offset * 0.42)
            height, exists = self._building(world_x, "distant")
            if exists:
                for y in range(max(0, ground - height), ground):
                    self.pixels[x, y] = distant_color

        for x in range(self.width):
            world_x = math.floor(x + self.scroll_offset)
            height, exists = self._building(world_x, "near")
            if not exists:
                continue
            roof = max(0, ground - height)
            for y in range(roof, ground):
                self.pixels[x, y] = near_color
                is_window_row = (y - roof) % 2 == 1
                lit = self._hash01(world_x, y, 101) < self.window_density * (0.12 + 0.88 * nightness)
                if is_window_row and lit:
                    self.pixels[x, y] = window_color

        # A dark street ties the two parallax layers together at the bottom.
        for x in range(self.width):
            road_light = self._hash01(math.floor(x + self.scroll_offset), salt=151) < 0.08 * nightness
            self.pixels[x, ground] = (74, 45, 27) if road_light else (9, 10, 15)

    def step(self, elapsed=None):
        """Advance the world by ``elapsed`` seconds and render one frame."""
        if elapsed is None:
            elapsed = self.frame_delay
        elapsed = min(1.0, max(0.0, float(elapsed)))
        self.scroll_offset += self.scroll_speed * elapsed
        self.cycle_elapsed += elapsed
        top, bottom, nightness, sunsetness = self._sky()
        self._draw_sky(top, bottom, nightness)
        self._draw_celestial_body(nightness, sunsetness)
        self._draw_buildings(nightness)

    def run(self):
        self._last_step_at = time.monotonic()
        while not self.should_stop():
            now = time.monotonic()
            self.step(now - self._last_step_at)
            self._last_step_at = now
            self.display()
            if not self.wait(self.frame_delay):
                break
