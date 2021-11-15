import sys
import pyaudio
from struct import unpack
import numpy as np
from PIL import Image
from display_modes import module
import time

class SpectrumAnalyzer(module.Module):
    """Pretty bargraph spectrum analyzer"""

    def __init__(self, driver):
        if driver.width != 16 or driver.height != 16:
            raise Exception(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)

        # Audio setup
        self.no_channels = 1
        self.sample_rate = 44100
        # self.sample_rate = 96000

        # Chunk must be a multiple of driver size
        # NOTE: If chunk size is too small the program will crash
        # with error message: [Errno Input overflowed]
        self.chunk = 2048

        # list_devices()
        # Use results from list_devices() to determine your microphone index
        self.device = 0

        self.pyaudio = pyaudio.PyAudio()
        self.stream = self.pyaudio.open(format = pyaudio.paInt16,
                        channels = self.no_channels,
                        rate = self.sample_rate,
                        input = True,
                        frames_per_buffer = self.chunk,
                        input_device_index = self.device)

    def _generate_bins(self, n_bins):
        x = 625**(1/float(n_bins))
        bins = [int(32*x**n) for n in range(0, n_bins + 1)]
        return bins
           
    def _calculate_levels(self, data, chunk, sample_rate):
           # Return power array index corresponding to a particular frequency
        def piff(val):
            return int(self.chunk*val/self.sample_rate)

        bins = self._generate_bins(self.driver.width)
        # Weighting to account for difference between linear response of microphone vs non-linear response of human ears
        weighting = [1, 1, 1, 2, 3, 4, 4, 4, 8, 8, 8, 16, 16, 16, 16, 16]
        matrix = [None] * 16

        # Gain multiplier
        gain = 60.0
        
        # Convert raw data (ASCII string) to numpy array
        data = unpack("%dh"%(len(data)/2),data)
        data = np.array(data, dtype='h')
        # Apply FFT - real data
        fourier=np.fft.rfft(data)
        # Remove last element in array to make it the same size as chunk
        fourier=np.delete(fourier,len(fourier)-1)
        # Find average 'amplitude' for specific frequency ranges in Hz
        power = np.abs(fourier)
        # print(f"Power: {power[piff(bins[1])]}")

        for n in range(len(matrix)):
            # print(f"piff: {piff(bins[n])}")
            # print(f"Slice: {power[piff(bins[n]):piff(bins[n+1])]}")
            matrix[n] = int(np.mean(power[piff(bins[n]):piff(bins[n+1]):1]))

        # print(matrix)
        # Tidy up column values for the LED matrix
        matrix=np.divide(np.multiply(matrix,weighting),1000000)
        # Set floor at 0 and ceiling height of matrix
        matrix = [int(n * gain) for n in matrix]
        matrix = np.clip(matrix, 0, self.driver.height)
        # print(matrix)
        return matrix

    def _generate_spectrums(self):
        """ Returns a list of fun spectrum colors to pick from """ 
        spectrum_GYR = [None] * 16
        spectrum_GYR[0:10] = [(0, 255, 0)] * 11
        spectrum_GYR[11:13] = [(255, 255, 0)] * 3
        spectrum_GYR[14:15] = [(255, 0, 0)] * 2
        return list([spectrum_GYR])

    def run(self):
        spectrums = self._generate_spectrums()
        # print(spectrums)

        # Main loop
        while True:
            start = time.time()
            # Get microphone data
            data = self.stream.read(self.chunk, exception_on_overflow=False)

            # Process data into a display matrix
            matrix = self._calculate_levels(data, self.chunk,self.sample_rate)

            self.driver.clear(self.image)
            for x in range (len(matrix)):
                for y in range(0, int(matrix[x])):
                    self.pixels[x, 15-y] = spectrums[0][y]
            self.display()
            stop = time.time()
            # print(f"FPS: {1.0/(stop - start)}")

    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio.terminate()
        super().cleanup()

