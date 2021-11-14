import sys
import pyaudio
from struct import unpack
import numpy as np
from PIL import Image
from display_modes import module

class SpectrumAnalyzer(module.Module):
    """Pretty bargraph spectrum analyzer"""

    def __init__(self, driver):
        if driver.width != 16 or driver.height != 16:
            raise Exception(f"Unacceptable Dimensions:{driver.width}x{driver.height}")
        super().__init__(driver)

        self.img = Image.new('RGB', (driver.width, driver.height), "black")
        self.pixels = self.img.load()

        # Audio setup
        self.no_channels = 1
        self.sample_rate = 44100

        # Chunk must be a multiple of 8
        # NOTE: If chunk size is too small the program will crash
        # with error message: [Errno Input overflowed]
        self.chunk = 3072 

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

    def run(self):
        while True:
            print("yeet")
           
    def __calculate_levels__(self, data, chunk, sample_rate):
           # Return power array index corresponding to a particular frequency
        def piff(val):
            return int(2*self.chunk*val/self.sample_rate)
        weighting = [2,8,8,16,16,32,32,64] 
        matrix = [None] * 16
        
        # Convert raw data (ASCII string) to numpy array
        data = unpack("%dh"%(len(data)/2),data)
        data = np.array(data, dtype='h')
        # Apply FFT - real data
        fourier=np.fft.rfft(data)
        # Remove last element in array to make it the same size as chunk
        fourier=np.delete(fourier,len(fourier)-1)
        # Find average 'amplitude' for specific frequency ranges in Hz
        power = np.abs(fourier)   
        matrix[0]= int(np.mean(power[piff(0)    :piff(156):1]))
        matrix[1]= int(np.mean(power[piff(156)  :piff(313):1]))
        matrix[2]= int(np.mean(power[piff(313)  :piff(625):1]))
        matrix[3]= int(np.mean(power[piff(625)  :piff(1250):1]))
        matrix[4]= int(np.mean(power[piff(1250) :piff(2500):1]))
        matrix[5]= int(np.mean(power[piff(2500) :piff(5000):1]))
        matrix[6]= int(np.mean(power[piff(5000) :piff(10000):1]))
        matrix[7]= int(np.mean(power[piff(10000):piff(20000):1]))
        matrix[8]= int(np.mean(power[piff(0)    :piff(156):1]))
        matrix[9]= int(np.mean(power[piff(156)  :piff(313):1]))
        matrix[10]= int(np.mean(power[piff(313)  :piff(625):1]))
        matrix[11]= int(np.mean(power[piff(625)  :piff(1250):1]))
        matrix[12]= int(np.mean(power[piff(1250) :piff(2500):1]))
        matrix[13]= int(np.mean(power[piff(2500) :piff(5000):1]))
        matrix[14]= int(np.mean(power[piff(5000) :piff(10000):1]))
        matrix[15]= int(np.mean(power[piff(10000):piff(20000):1]))
        # Tidy up column values for the LED matrix
        matrix=np.divide(np.multiply(matrix,weighting),1000000)
        # Set floor at 0 and ceiling at 8 for LED matrix
        matrix = [n * 50 for n in matrix]
        matrix = matrix.clip(0, 16)
        print(matrix)
        return matrix

    def run(self):
        spectrum  = [1,1,1,3,3,3,2,2]
        matrix    = [0,0,0,0,0,0,0,0]
        power     = []
        weighting = [2,8,8,16,16,32,32,64] 

        # Main loop
        while 1:
            try:
                # Get microphone data
                data = self.stream.read(self.chunk)
                matrix=self.__calculate_levels__(data, self.chunk,self.sample_rate)
                self.driver.clear(self.img)
                for y in range (len(matrix)):
                    for x in range(0, int(matrix[y])):
                        # self.pixels[x,y] = spectrum[x]
                        self.pixels[y, x] = (0, 255, 0)
                self.driver.display(self.img)
            except KeyboardInterrupt:
                print("Ctrl-C Terminating...")
                self.stream.stop_stream()
                self.stream.close()
                self.pyaudio.terminate()
                sys.exit(1)

