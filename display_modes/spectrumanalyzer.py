import pyaudio
from struct import unpack
import numpy as np
from PIL import Image
from display_modes import module
import time
import colorlog
import re
import subprocess

logger = colorlog.getLogger(__name__)


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

        def get_device(target_name="snd_rpi_i2s_card") -> int:
            cmd = "arecord -l"
            ret_val = subprocess.check_output(cmd, shell=True).decode("utf-8")
            match = re.search(r'card (\d+)', ret_val)
            logger.info(f"{cmd}\n{ret_val}")
            return int(match.group(1))

            # p = pyaudio.PyAudio()

            # # Search for device with name starting with target_name
            # for dev_id in range(p.get_device_count()):
            #     name: str = p.get_device_info_by_index(dev_id)['name']
            #     if name.startswith(target_name):
            #         logger.info(f"Found I2S device {name} with ID {dev_id}")
            #         p.terminate()
            #         return dev_id

            # # Did not find target name
            # raise Exception(f"Did not find device with name {target_name}")
            # return 0

        # Use results from list_devices() to determine your microphone index
        # self.device = get_device()
        self.device = 1

        self.pyaudio = pyaudio.PyAudio()
        self.stream = self.pyaudio.open(format=pyaudio.paInt16,
                                        channels=self.no_channels,
                                        rate=self.sample_rate,
                                        input=True,
                                        frames_per_buffer=self.chunk,
                                        input_device_index=self.device)
        # stream = p.open(format = pyaudio.paInt16, channels = 1, rate = 44100, input = True, frames_per_buffer = 2048, input_device_index = 1)

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
        weighting = [1, 1, 1, 1, 2, 3, 4, 4, 8, 8, 8, 20, 22, 24, 26, 30]
        matrix = [None] * 16

        # Gain multiplier
        gain = 80.0
        
        # Convert raw data (ASCII string) to numpy array
        data = unpack("%dh" % (len(data)/2), data)
        data = np.array(data, dtype='h')
        # Apply FFT - real data
        fourier = np.fft.rfft(data)
        # Remove last element in array to make it the same size as chunk
        fourier = np.delete(fourier, len(fourier)-1)
        # Find average 'amplitude' for specific frequency ranges in Hz
        power = np.abs(fourier)
        # print(f"Power: {power[piff(bins[1])]}")

        for n in range(len(matrix)):
            # print(f"piff: {piff(bins[n])}")
            # print(f"Slice: {power[piff(bins[n]):piff(bins[n+1])]}")
            matrix[n] = int(np.mean(power[piff(bins[n]):piff(bins[n+1]):1]))

        # print(matrix)
        # Tidy up column values for the LED matrix
        matrix = np.divide(np.multiply(matrix, weighting), 1000000)
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
            logger.info(data)

            # Process data into a display matrix
            matrix = self._calculate_levels(data, self.chunk, self.sample_rate)

            self.driver.clear(self.image)
            for x in range(len(matrix)):
                for y in range(0, int(matrix[x])):
                    self.pixels[x, 15-y] = spectrums[0][y]
            self.display()
            stop = time.time()
            fps = 1.0/(stop - start)
            logger.info(f"FPS: {fps:.2f}")

    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio.terminate()
        super().cleanup()
