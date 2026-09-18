"""A warm, animated fireplace using a rising cellular heat simulation."""

import random

from display_modes import module
from mode_settings import FIREPLACE_SETTINGS, hex_to_rgb, normalize_settings


PALETTES = {
    "classic": ("#120000", "#B51A05", "#FF6A00", "#FFF2A1"),
    "hearth": ("#160000", "#8C1200", "#F04A00", "#FFD166"),
    "candle": ("#1A0800", "#D35400", "#FFB000", "#FFF8D6"),
    "blue_flame": ("#00051A", "#003C78", "#00A6D6", "#B6F4FF"),
    "neon": ("#18002E", "#B00070", "#FF3D71", "#FFD166"),
}


class Fireplace(module.Module):
    """Render fire by injecting heat at the base and letting it rise and cool."""

    LOG_DARK = (45, 16, 8)
    LOG_LIGHT = (105, 39, 13)

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.embers = []
        self.random = random.Random()
        self.heat = [[0.0 for _ in range(self.width)] for _ in range(max(1, self.height - 2))]
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

    def _palette_color(self, value):
        position = min(1.0, max(0.0, value)) * (len(self.palette) - 1)
        index = min(len(self.palette) - 2, int(position))
        amount = position - index
        start, end = self.palette[index], self.palette[index + 1]
        return tuple(round(first + (second - first) * amount) for first, second in zip(start, end))

    def _inject_heat(self):
        """Create an uneven, flickering bed of heat immediately above the logs."""
        bottom = len(self.heat) - 1
        # Broad pulses make coherent flame roots; flicker adds local variation.
        pulse_width = max(2, round(self.width * (0.12 + (1.0 - self.flame_scale) * 0.18)))
        pulses = max(1, round(self.width / max(4, pulse_width * 2)))
        sources = []
        for _ in range(pulses):
            sources.append((
                self.random.randrange(self.width),
                self.random.uniform(0.68, 1.0),
                self.random.uniform(max(1.0, pulse_width * 0.6), max(1.1, pulse_width * 1.3)),
            ))

        for x in range(self.width):
            base = self.random.uniform(0.20, 0.42)
            for center, strength, radius in sources:
                distance = abs(x - center)
                distance = min(distance, self.width - distance)
                if distance < radius:
                    base = max(base, strength * (1.0 - 0.55 * distance / radius))
            jitter = self.random.uniform(-0.12, 0.12) * self.flicker
            self.heat[bottom][x] = min(1.0, max(0.0, base + jitter))

    def _advance_heat(self):
        """Advect heat upward with cooling, diffusion and small lateral drift."""
        rows = len(self.heat)
        if rows <= 1:
            self._inject_heat()
            return

        old = self.heat
        new = [[0.0 for _ in range(self.width)] for _ in range(rows)]

        # Higher flame_height means slower cooling and therefore taller flames.
        cooling = 0.055 + (1.0 - self.flame_height) * 0.18
        lateral = 0.08 + self.turbulence * 0.22

        for y in range(rows - 1):
            below_y = min(rows - 1, y + 1)
            two_below_y = min(rows - 1, y + 2)
            for x in range(self.width):
                # Pick a tiny random drift per cell. Unlike scrolling noise this
                # changes the flame's path rather than translating its texture.
                drift = self.random.choices((-1, 0, 1), (self.turbulence, 2.0, self.turbulence))[0]
                source_x = (x + drift) % self.width
                center = old[below_y][source_x]
                deeper = old[two_below_y][source_x]
                left = old[below_y][(source_x - 1) % self.width]
                right = old[below_y][(source_x + 1) % self.width]
                value = center * (0.58 - lateral * 0.35)
                value += deeper * 0.25
                value += (left + right) * lateral * 0.5
                value -= cooling * self.random.uniform(0.75, 1.25)
                new[y][x] = min(1.0, max(0.0, value))

        self.heat = new
        self._inject_heat()

    def _draw_flames(self):
        rows = len(self.heat)
        for y in range(rows):
            # Suppress weak residual heat so the top of each tongue has a
            # distinct edge instead of a full-screen haze.
            height_fraction = (rows - 1 - y) / max(1, rows - 1)
            threshold = 0.06 + height_fraction * 0.06
            for x in range(self.width):
                heat = self.heat[y][x]
                if heat > threshold:
                    self.pixels[x, y] = self._palette_color((heat - threshold) / (1.0 - threshold))

    def _draw_logs(self):
        if self.height < 2:
            return
        for x in range(self.width):
            self.pixels[x, self.height - 1] = self.LOG_DARK
            self.pixels[x, self.height - 2] = self.LOG_LIGHT if x % 3 else self.LOG_DARK
        if self.width >= 6:
            for x in range(2, self.width - 2):
                self.pixels[x, self.height - 2] = self.LOG_LIGHT

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
        self._advance_heat()
        self._draw_flames()
        self._draw_logs()
        self._update_embers()

    def run(self):
        while not self.should_stop():
            self.step()
            self.display()
            if not self.wait(self.frame_delay):
                break
