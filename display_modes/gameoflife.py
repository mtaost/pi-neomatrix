import random
from display_modes import module
from datetime import datetime
import time


class GameOfLife(module.Module):
    """Life"""

    ALIVE = (150, 50, 150)
    DEAD = (0, 0, 0)

    def __init__(self, driver):
        if driver.width != 16 or driver.height != 16:
            raise Exception(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)
        random.seed(datetime.now())
        self.state = [list([0 for i in range(self.height)]) for j in range(self.width)]
        self.randomize()
        self.red = 240
        self.green = 0
        self.blue = 0
        self.cycleCount = 0
        self.prevChanges = 0
        self.colorstep = 10
        self.delay = 0.05

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

    def detectCycle(self, changes):
        if changes == self.prevChanges:
            self.cycleCount += 1
        else:
            self.cycleCount = 0
            self.prevChanges = changes
        if self.cycleCount == 50:
            self.randomize()
    
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
        RAINBOW = (self.red, self.green, self.blue)
        if self.red > 0 and self.blue == 0:
            self.red -= self.colorstep
            self.green += self.colorstep
        else:
            if self.green > 0:
                self.green -= self.colorstep
                self.blue += self.colorstep
            else:
                self.blue -= self.colorstep
                self.red += self.colorstep
        for x in range(self.width):
            for y in range(self.height):
                self.pixels[x, y] = RAINBOW if self.state[x][y] else GameOfLife.DEAD
        super().display()
    
    def run(self):
        self.display()
        time.sleep(0.5)
        while 1:
            time.sleep(self.delay)
            self.advanceState()
            self.display()
