# pi-neomatrix
Multipurpose 2ft by 2ft LED display driven by Raspberry Pi, capable of showing images, videos, simulations, and other visually pleasing displays!

There are many pixel displays out there, but not as many which are this large, which required custom electronics and mounting solutions to accommodate a 3cmx3cm pixel size while not making everything a rat's nest of wires.

![alt text](https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/gol_demo.gif "Display playing Conways Game of Life")

One main goal of the software architecture is to abstract the hardware interactions to a library so one can more easily develop, test, and deploy display modalities. Currently, the display has the following modes developed:

- Image viewer supporting gifs
- Game of life
- Pixel rain display
- FFT audio spectrum analyzer
- Thermal camera
- Falling pixels rain
- Shimmering starry night display
- Tetris AI bot

Below are gifs showing off the soothing pixel rain, and the slightly chaotic multiplayer Tetris AI bot:
  
<img src="https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/rain_demo.gif" alt="Pixel rain" width="800">
<img src="https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/tetris_demo.gif" alt="Pixel rain" width="800">
  
## Construction ##
The core component of the display is the WS2811/WS2812b LED chip. Known as a NeoPixel to some, this IC allows one to individually control theoretically infinite LEDs through a single wire, though in practice, propogation delays will cause latency issues at larger pixel counts. 

For my display, 16 strips of 16 leds spaced 33mm apart are laid down a plastic backing and snake around to minimize the wires. 

![alt text](https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/board_1.jpg?raw=true "Base board with led strips")

Then, a grid of dividers created using a laser cutter and cardstock is laid on top of the grid to give distinct separation between pixels. 

![alt text](https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/board_4.jpg?raw=true "Dividers")

For this project, 16x16=256 pixels is not enough to worry about refresh rate issues due to high latency between pixels, but it is enough pixels to worry about power consumption.

At full brightness values (255, 255, 255), each pixel can draw 60mA totalling to 15.36A. In practice though, there are few situations where we will be displaying all 256 pixels at max brightness, and some voltage drawdown is acceptable. However, it's important to make sure that pixels do not get less voltage the further they are on the chain

To deliver power evenly to each row, I created a power bus bar sort of layout which has 2 pieces of copper tape that provide +5V and GND to each row of pixels. 

![alt text](https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/board_2.jpg?raw=true "Power bus")

The electronics are held on the back by a combination of DIN rails and 3d printed DIN clips, which neatly hold the power supply, RPi, and other related circuitry in place

![alt text](https://github.com/mtaost/pi-neomatrix/blob/master/repo_images/din_0.jpg?raw=true "DIN Rail")

## Hardware Setup ##
Required hardware:

- Raspberry Pi 3 B+
- HW-221 Level shifter
- 16x16 WS2812 matrix
- INMP441 I2S MEMS Microphone
- BH1750 Light sensor
- MLX90640 IR Thermal Camera

## Sofware Setup ##
To get started, set up a Raspberry Pi using the Raspian lite OS and connect it to your network using `raspi-config`. In raspi-config, go to interface and enable SSH, I2C, and SPI, then connect to WiFi.

Run `sudo apt-get update` to update the OS and then ensure SSH access before disconnecting the Raspberry Pi from your display if you wish to use the device remotely. 
Run `sudo apt install python3-pip` to get pip 

`sudo pip3 install -r requirements.txt`

Numpy for raspberry pi
```bash
$ sudo apt-get install libopenjp2-7
```

Setting up the I2S microphone:
https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test
https://makersportal.com/shop/i2s-mems-microphone-for-raspberry-pi-inmp441
