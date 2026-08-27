"""A smooth, evenly-spaced pixel rain animation."""

import colorsys
import math
import random
import time

from display_modes import module
from mode_settings import PIXEL_RAIN_SETTINGS, hex_to_rgb, normalize_settings


class PixelRain(module.Module):
    """Render falling drops with fractional positions and soft trails.

    The old implementation shifted the whole image once per sleep interval and
    made an independent random spawn decision for every column. That made all
    drops move in lockstep while their starts tended to clump together. Drops
    here have their own positions, and a shuffled full-column scheduler keeps
    coverage even without forming a repeating diagonal pattern.
    """

    TARGET_FPS = 60
    MAX_ELAPSED = 0.25
    MAX_PARTICLES = 64
    DENSITY_SATURATION = 8.0
    DENSITY_SLIDER_BREAKPOINT = 0.5
    DENSITY_BEHAVIOR_BREAKPOINT = 0.1
    SPAWN_JITTER = (0.75, 1.25)
    # A deterministic pattern avoids reintroducing clumps while providing
    # enough variation to make the streams feel organic. The mean is exactly
    # 1.0, so enabling this does not change the overall rain speed.
    SPEED_FACTORS = (0.8, 1.0, 1.2, 0.9, 1.1, 0.85, 1.15)

    # These are intentionally the same gradients used by SpectrumAnalyzer,
    PALETTES = {
        "ocean": ((0, 255, 220), (0, 110, 255), (180, 0, 255)),
        "sunset": ((255, 230, 100), (255, 120, 55), (235, 35, 110)),
        "twilight": ((18, 0, 48), (112, 30, 190), (245, 40, 145), (70, 155, 255)),
    }

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.drops = []
        self.rainbow_phase = 0.0
        self._random = random.Random()
        self._column_order = []
        self._column_index = 0
        self._last_column = None
        self._next_speed_factor = 0
        # Start with one scheduled drop so the display does not sit blank
        # while the first interval elapses.
        self._spawn_credit = 1.0
        self._spawn_threshold = 1.0
        self._legacy_color_mode = None
        self.update_settings(options)

    def update_settings(self, values=None):
        raw_values = {} if values is None else values
        self.settings = normalize_settings(PIXEL_RAIN_SETTINGS, raw_values, getattr(self, "settings", None))

        was_variable_speed = getattr(self, "variable_drop_speed", False)
        self.frame_delay = self.settings["frame_delay"]
        self.variable_drop_speed = self.settings["variable_drop_speed"]
        self.density = int(self.settings["density"])
        self.persistence = self.settings["persistence"]
        self.trail_length_variance = self.settings["trail_length_variance"]
        self.drop_brightness_variance = self.settings["drop_brightness_variance"]
        self.palette = self.settings["palette"]
        self.fixed_color = hex_to_rgb(self.settings["fixed_color"])

        # Accept the pre-palette settings used by older callers and saved
        # configurations when they are supplied without a new palette.
        self._legacy_color_mode = None
        if "palette" not in raw_values and "rain_color_mode" in raw_values:
            self._legacy_color_mode = raw_values["rain_color_mode"]
            if self._legacy_color_mode == "fixed":
                self.palette = "fixed"
                self.fixed_color = hex_to_rgb(raw_values["rain_fixed_color"])
            elif self._legacy_color_mode == "rainbow_gradient":
                self.palette = "rainbow_gradient"

        # Keep these values available for old callers that still send them.
        self.rainbow_cycle_speed = self.settings["rainbow_cycle_speed"]
        self.rainbow_gradient_speed = self.settings["rainbow_gradient_speed"]
        density_fraction = self._density_behavior_fraction(self.density)
        # Keep low settings useful while compressing the extreme upper end.
        # This controls visible occupancy instead of multiplying both
        # occupancy and render work linearly all the way to 1,000.
        effective_density = density_fraction / (1.0 + self.DENSITY_SATURATION * density_fraction)
        reference_density = 30 / 1000.0
        effective_density *= 1.0 + self.DENSITY_SATURATION * reference_density
        self.spawn_rate = self.width * effective_density / max(self.frame_delay, 0.001)
        self.trail_brightness = self._build_trail_brightness()
        # One row per old animation interval keeps the speed control familiar,
        # while the render loop can now sample the motion more frequently.
        self.drop_speed = 1.0 / max(self.frame_delay, 0.001)
        if was_variable_speed and not self.variable_drop_speed:
            for drop in self.drops:
                drop["speed_factor"] = 1.0
        return dict(self.settings)

    def _build_trail_brightness(self):
        self.base_trail_length = min(
            self.height + 1,
            max(1, math.ceil(math.log(0.03) / math.log(self.persistence))),
        )
        return tuple(self.persistence**distance for distance in range(self.height + 1))

    @classmethod
    def _density_behavior_fraction(cls, control_value):
        """Expand the light-rain portion of the density slider.

        The first half of the control covers the behavior that previously
        occupied its first ten percent. The upper half retains the old
        10–100% range so high-density settings remain useful.
        """
        control_fraction = min(1.0, max(0.0, control_value / 1000.0))
        if control_fraction <= cls.DENSITY_SLIDER_BREAKPOINT:
            return control_fraction * (
                cls.DENSITY_BEHAVIOR_BREAKPOINT / cls.DENSITY_SLIDER_BREAKPOINT
            )
        upper_progress = (control_fraction - cls.DENSITY_SLIDER_BREAKPOINT) / (
            1.0 - cls.DENSITY_SLIDER_BREAKPOINT
        )
        return cls.DENSITY_BEHAVIOR_BREAKPOINT + upper_progress * (
            1.0 - cls.DENSITY_BEHAVIOR_BREAKPOINT
        )

    @staticmethod
    def _interpolate(stops, position):
        position = min(1.0, max(0.0, position))
        scaled = position * (len(stops) - 1)
        lower = min(len(stops) - 2, int(scaled))
        blend = scaled - lower
        start, end = stops[lower], stops[lower + 1]
        return tuple(round(first + (last - first) * blend) for first, last in zip(start, end))

    @staticmethod
    def _rainbow_color(hue):
        return tuple(round(channel * 255) for channel in colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0))

    def _palette_color(self, position):
        """Return a color from a non-rainbow palette at a vertical position."""
        return self._interpolate(self.PALETTES[self.palette], position)

    def _color_at(self, x, y):
        """Map a display position to the selected palette."""
        if self._legacy_color_mode == "rainbow_cycle":
            return self._rainbow_color(self.rainbow_phase)
        if self.palette == "fixed":
            return self.fixed_color
        if self.palette == "rainbow_gradient":
            hue = x / max(self.width, 1) + (y / max(self.height - 1, 1)) * 0.18
            return self._rainbow_color(hue + self.rainbow_phase)
        return self._palette_color(y / max(self.height - 1, 1))

    def _spawn_color(self, x, y=0):
        """Compatibility helper retained for callers and existing tests."""
        return self._color_at(x, y)

    def _spawn_drop(self, x):
        if self.variable_drop_speed:
            speed_factor = self.SPEED_FACTORS[self._next_speed_factor % len(self.SPEED_FACTORS)]
            self._next_speed_factor += 1
        else:
            speed_factor = 1.0
        trail_factor = 1.0 + self._random.uniform(-0.5, 0.5) * self.trail_length_variance
        trail_length = min(
            len(self.trail_brightness),
            max(1, round(self.base_trail_length * trail_factor)),
        )
        brightness_factor = 1.0 + self._random.uniform(-0.5, 0.5) * self.drop_brightness_variance
        self.drops.append({
            "x": x,
            "y": 0.0,
            "speed_factor": speed_factor,
            "trail_length": trail_length,
            "brightness_factor": brightness_factor,
        })

    def _shuffle_columns(self):
        self._column_order = list(range(self.width))
        self._random.shuffle(self._column_order)
        if (
            self._last_column is not None
            and len(self._column_order) > 1
            and self._column_order[0] == self._last_column
        ):
            self._column_order[0], self._column_order[1] = self._column_order[1], self._column_order[0]
        self._column_index = 0

    def _next_spawn_column(self):
        if self._column_index >= len(self._column_order):
            self._shuffle_columns()
        column = self._column_order[self._column_index]
        self._column_index += 1
        self._last_column = column
        return column

    def _schedule_spawns(self, elapsed):
        self._spawn_credit += elapsed * self.spawn_rate
        while self._spawn_credit >= self._spawn_threshold and len(self.drops) < self.MAX_PARTICLES:
            self._spawn_credit -= self._spawn_threshold
            self._spawn_drop(self._next_spawn_column())
            self._spawn_threshold = self._random.uniform(*self.SPAWN_JITTER)
        if len(self.drops) >= self.MAX_PARTICLES:
            self._spawn_credit = min(self._spawn_credit, self._spawn_threshold)

    def _update_drops(self, elapsed):
        for drop in self.drops:
            drop["y"] += self.drop_speed * drop.get("speed_factor", 1.0) * elapsed
        # A drop can remain partly visible after its head leaves the panel.
        self.drops = [
            drop
            for drop in self.drops
            if drop["y"] - drop.get("trail_length", self.base_trail_length) <= self.height
        ]

    def _blend_pixel(self, x, y, color, brightness):
        if not 0 <= x < self.width or not 0 <= y < self.height or brightness <= 0:
            return
        scaled = tuple(round(channel * min(1.0, brightness)) for channel in color)
        existing = self.pixels[x, y]
        # Adjacent anti-aliased trail samples can contribute to the same row.
        # Add them instead of choosing whichever happens to be brighter; the
        # latter causes a sawtooth brightness pulse as a drop crosses a row.
        self.pixels[x, y] = tuple(min(255, old + new) for old, new in zip(existing, scaled))

    def _draw_sample(self, x, position, brightness):
        """Draw one anti-aliased trail sample between two matrix rows."""
        lower = math.floor(position)
        fraction = position - lower
        self._blend_pixel(x, lower, self._color_at(x, lower), brightness * (1.0 - fraction))
        self._blend_pixel(x, lower + 1, self._color_at(x, lower + 1), brightness * fraction)

    def _render_drops(self):
        self.image.paste((0, 0, 0), (0, 0, self.width, self.height))
        for drop in self.drops:
            trail_length = drop.get("trail_length", self.base_trail_length)
            brightness_factor = drop.get("brightness_factor", 1.0)
            for distance, brightness in enumerate(self.trail_brightness[:trail_length]):
                self._draw_sample(
                    drop["x"],
                    drop["y"] - distance,
                    brightness * brightness_factor,
                )

    def step(self, elapsed):
        """Advance and render one frame using elapsed wall-clock seconds."""
        elapsed = min(self.MAX_ELAPSED, max(0.0, float(elapsed)))
        self._update_drops(elapsed)
        self._schedule_spawns(elapsed)
        self._render_drops()
        if self._legacy_color_mode == "rainbow_cycle":
            self.rainbow_phase = (self.rainbow_phase + self.rainbow_cycle_speed * elapsed) % 1.0
        elif self._legacy_color_mode == "rainbow_gradient":
            self.rainbow_phase = (self.rainbow_phase + self.rainbow_gradient_speed * elapsed) % 1.0

    def run(self):
        """Render on a monotonic schedule instead of sleeping per movement step."""
        frame_interval = 1.0 / self.TARGET_FPS
        previous = time.monotonic()
        next_frame = previous
        while not self.should_stop():
            now = time.monotonic()
            if now < next_frame:
                if not self.wait(next_frame - now):
                    break
                continue

            self.step(now - previous)
            previous = now
            self.display()
            next_frame += frame_interval
            if next_frame <= now:
                next_frame = now + frame_interval
