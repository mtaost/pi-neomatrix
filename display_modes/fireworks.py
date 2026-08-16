import math
import random

from display_modes import module
from mode_settings import FIREWORKS_SETTINGS, normalize_settings


PALETTES = {
    "classic": ((255, 80, 40), (255, 190, 40), (80, 160, 255), (255, 255, 255)),
    "warm": ((255, 40, 20), (255, 100, 20), (255, 190, 40), (255, 220, 150)),
    "cool": ((40, 100, 255), (40, 220, 255), (100, 120, 255), (180, 255, 255)),
    "patriotic": ((255, 40, 40), (255, 255, 255), (40, 100, 255)),
    "neon": ((255, 40, 180), (80, 255, 160), (80, 150, 255), (255, 240, 40)),
}


class Fireworks(module.Module):
    """Continuous 16×16 firework rockets, trails, and particle bursts."""

    def __init__(self, driver, options=None):
        super().__init__(driver)
        self.particles = []
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(FIREWORKS_SETTINGS, values, getattr(self, "settings", None))
        self.frame_delay = self.settings["frame_delay"]
        self.launch_rate = self.settings["launch_rate"]
        self.burst_size = int(self.settings["burst_size"])
        self.trail_persistence = self.settings["trail_persistence"]
        self.gravity = self.settings["gravity"]
        self.launch_speed = self.settings["launch_speed"]
        self.burst_speed = self.settings["burst_speed"]
        self.palette = PALETTES[self.settings["palette"]]

        self.fade_to_color = self.settings["fade_to_color"]

        return dict(self.settings)

    def _fade(self):
        for y in range(self.height):
            for x in range(self.width):
                color = self.pixels[x, y]
                self.pixels[x, y] = tuple(int(channel * self.trail_persistence) for channel in color)

    def _launch_rocket(self):
        life = random.randint(5, 9)
        self.particles.append({"kind": "rocket", "x": random.uniform(2, self.width - 3), "y": float(self.height - 1), "vx": random.uniform(-0.12, 0.12), "vy": -self.launch_speed, "life": life, "max_life": life, "color": random.choice(self.palette)})

        self.particles[-1]["burst_color"] = random.choice(self.palette)

        burst_color = self.particles[-1]["burst_color"]
        target_colors = [color for color in self.palette if color != burst_color]
        self.particles[-1]["fade_color"] = random.choice(target_colors) if self.fade_to_color else burst_color

    def _explode(self, rocket):
        for index in range(self.burst_size):
            angle = math.tau * index / self.burst_size + random.uniform(-0.06, 0.06)
            speed = self.burst_speed * random.uniform(0.9, 1.05)
            life = random.randint(8, 18)
            self.particles.append({"kind": "spark", "x": rocket["x"], "y": rocket["y"], "vx": math.cos(angle) * speed, "vy": math.sin(angle) * speed, "life": life, "max_life": life, "color": random.choice(self.palette)})

            self.particles[-1]["color"] = rocket["burst_color"]

            self.particles[-1]["fade_color"] = rocket["fade_color"]

    def _draw(self, particle):
        x, y = round(particle["x"]), round(particle["y"])
        if 0 <= x < self.width and 0 <= y < self.height:
            factor = particle["life"] / particle["max_life"]
            if "fade_color" in particle:
                progress = 1 - factor
                color = tuple(round(start * (1 - progress) + end * progress) for start, end in zip(particle["color"], particle["fade_color"]))
                self.pixels[x, y] = tuple(round(channel * factor) for channel in color)
                return

            self.pixels[x, y] = tuple(round(channel * factor) for channel in particle["color"])

    def step(self):
        self._fade()
        if random.random() < self.launch_rate * self.frame_delay:
            self._launch_rocket()
        remaining = []
        for particle in self.particles:
            if particle["kind"] == "rocket":
                self._draw(particle)
                particle["x"] += particle["vx"]
                particle["y"] += particle["vy"]
                particle["life"] -= 1
                if particle["life"] <= 0 or particle["y"] <= 2:
                    self._explode(particle)
                else:
                    remaining.append(particle)
                continue
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["vy"] += self.gravity
            particle["life"] -= 1
            if particle["life"] > 0:
                self._draw(particle)
                remaining.append(particle)
        self.particles = remaining

    def run(self):
        while not self.should_stop():
            self.step()
            self.display()
            if not self.wait(self.frame_delay): break
