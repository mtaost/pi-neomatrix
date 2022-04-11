from display_modes import module
import board
import busio
import adafruit_mlx90640
from PIL import Image
from numpy import linspace

import time

class ThermalCamera(module.Module):
    def __init__(self, driver):
        super().__init__(driver)
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=640000)
        self.mlx = adafruit_mlx90640.MLX90640(self.i2c)
        print("MLX addr detected on I2C")
        print([hex(i) for i in self.mlx.serial_number])
        self.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_16_HZ
        self.thermal_data = [0] * 768
        self.thermal_image = Image.new('RGB', (32, 24), 'black')
        self.thermal_pixels = self.thermal_image.load()
        self.driver = driver
        self.color_map_rainbow = self._generate_rainbow_map(100, 20, 32)
        self.autorange = True

    # Returns a new map which linearly interpolates a temperature color mapping
    def _interpolate_map(self, map):
        return map

    # Returns a rainbow map of n-3 colors mapped to temperature between tstart and tstop
    def _generate_rainbow_map(self, n, t_start, t_stop):
        temp_increments = linspace(t_start, t_stop, n-3)
        color_increments = self._generate_rainbow_colors(int(n/4))
        color_increments.reverse()
        temp_map = {temp_increments[i]: color_increments[i] for i in range(len(temp_increments))}

        return temp_map

    # Generates n*4-3 number of gradually rainbow color tuples where there are n color increments
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
        return color_list

    # Returns a tuple color based on given color mapping dict
    def _get_color(self, temp, map):
        # Return the first value that is above the temperature
        for key in map.keys():
            if temp < key:
                return map[key]

        # Otherwise return the last temperature
        return map[list(map.keys())[-1]]
        
    def run(self):
        autorange_counter = 0
        while 1:
            try:
                self.mlx.getFrame(self.thermal_data)
                if self.autorange:
                    if autorange_counter == 0:
                        max_temp = max(self.thermal_data)
                        min_temp = min(self.thermal_data)
                        self.color_map_rainbow = self._generate_rainbow_map(100, min_temp, max_temp)
                    elif autorange_counter >= 4:
                        autorange_counter = 0
                    else:
                        autorange_counter += 1
            except Exception:
            # these happen, no biggie - retry
                continue
            

            # Get thermal data and insert it into thermal_image 
            for h in range(24):
                for w in range(32):
                    temp = self.thermal_data[h * 32 + w]
                    self.thermal_pixels[w, h] = self._get_color(temp, self.color_map_rainbow)
            
            # Resize thermal image to display dimensions
            resize_thermal_image = self.thermal_image.copy()
            self.image = resize_thermal_image.resize((self.driver.width, self.driver.height))
            self.display()