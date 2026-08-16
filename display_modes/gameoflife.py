import colorsys
from mode_settings import GAME_OF_LIFE_SETTINGS, hex_to_rgb, normalize_settings
from collections import deque
import random
from display_modes import module
from datetime import datetime
import time


class GameOfLife(module.Module):
    """Life"""

    MAX_CYCLE_PERIOD = 4
    CYCLE_REPEAT_LIMIT = 50
    ALIVE = (150, 50, 150)
    DEAD = (0, 0, 0)

    def __init__(self, driver, options=None):
        if driver.width != 16 or driver.height != 16:
            raise Exception(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)
        random.seed(int(datetime.now().timestamp()))
        self.state = [list([0 for i in range(self.height)]) for j in range(self.width)]
        self.randomize()
        self.red = 240
        self.green = 0
        self.blue = 0
        self.cycleCount = 0
        self.cycle_period = None
        self._state_history = deque((self._state_signature(),), maxlen=self.MAX_CYCLE_PERIOD)
        self.colorstep = 10
        self.delay = 0.05

        self.rainbow_phase = 0.0
        self.update_settings(options)

    def update_settings(self, values=None):
        self.settings = normalize_settings(GAME_OF_LIFE_SETTINGS, values, getattr(self, "settings", None))
        self.delay = self.settings["iteration_delay"]
        self.alive_color_mode = self.settings["alive_color_mode"]
        self.alive_fixed_color = hex_to_rgb(self.settings["alive_fixed_color"])
        self.dead_color = hex_to_rgb(self.settings["dead_color"])
        self.rainbow_cycle_speed = self.settings["rainbow_cycle_speed"]
        self.rainbow_gradient_speed = self.settings["rainbow_gradient_speed"]
        return dict(self.settings)

    def _rainbow_color(self, hue):
        red, green, blue = colorsys.hsv_to_rgb(hue % 1.0, 1.0, 1.0)
        return tuple(round(channel * 255) for channel in (red, green, blue))

    def _alive_color(self, x, y):
        if self.alive_color_mode == "fixed":
            return self.alive_fixed_color
        if self.alive_color_mode == "rainbow_cycle":
            return self._rainbow_color(self.rainbow_phase)
        gradient = (x / self.width + y / self.height) / 2
        return self._rainbow_color(self.rainbow_phase + gradient)

    def randomize(self):
        for x in range(self.width):
            for y in range(self.height):
                self.state[x][y] = random.randint(0,1) 
    
    def advanceState(self):
        nextState = [list([0 for i in range(self.height)]) for j in range(self.width)]
        count = 0
        for i in range(self.width):
            for j in range(self.height):
                nextState[i][j], change = self.aliveCell(i,j)
                count += change
        self.state = nextState
        self.detectCycle(count)

    def _state_signature(self):
        return tuple(tuple(column) for column in self.state)

    def detectCycle(self, changes):
        signature = self._state_signature()
        self.cycle_period = next(
            (
                period
                for period, prior_state in enumerate(reversed(self._state_history), start=1)
                if signature == prior_state
            ),
            None,
        )

        if self.cycle_period is not None:
            self.cycleCount += 1
        else:
            self.cycleCount = 0
        self._state_history.append(signature)

        if self.cycleCount >= self.CYCLE_REPEAT_LIMIT:
            self.randomize()
            self._state_history.clear()
            self._state_history.append(self._state_signature())
            self.cycleCount = 0
            self.cycle_period = None

        return self.cycle_period

    def aliveCell(self, row, col):
        currCell = self.state[row][col]
        count = 0
        
        if (row == 0 or col == 0 or row == self.width-1 or col == self.height-1):
            for i in range (-1, 2):
                for j in range (-1, 2):
                    x = i + row
                    y = j + col
                    if x == -1: 
                        x = self.width - 1
                    elif x == self.width:
                        x = 0
                    if y == -1:
                        y = self.height - 1
                    elif y == self.height:
                        y = 0
                    if self.state[x][y]:
                        count += 1
        else:
            for i in range (-1, 2):
                for j in range (-1, 2):
                    if self.state[i + row][j + col]:
                        count += 1
        if currCell:
            if count == 3 or count == 4:
                return (1, 0)
            return (0, 1)
        else:
            if count == 3:
                return (1, 1)
            return (0, 0)

    def display(self):
        speed = self.rainbow_cycle_speed if self.alive_color_mode == "rainbow_cycle" else self.rainbow_gradient_speed
        self.rainbow_phase = (self.rainbow_phase + speed * self.delay) % 1.0
        for x in range(self.width):
            for y in range(self.height):
                self.pixels[x, y] = self._alive_color(x, y) if self.state[x][y] else self.dead_color
        super().display()

    def run(self):
        self.display()
        if not self.wait(0.5):
            return
        while not self.should_stop():
            if not self.wait(self.delay):
                break
            self.advanceState()
            self.display()
