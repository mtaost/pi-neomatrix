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

## Software Setup ##

### Initial Raspberry Pi Setup
1. Set up a Raspberry Pi using the Raspbian OS and connect it to your network
2. Run `sudo raspi-config` and enable the following interfaces:
   - SSH
   - I2C
   - SPI
3. Connect to WiFi through `raspi-config`

### Install Dependencies

#### System packages
```bash
sudo apt update
sudo apt install -y python3-pip python3-dev libopenjp2-7 python3-pyaudio
```

#### Python packages
```bash
cd /path/to/pi-neomatrix
sudo pip install -r requirements.txt --break-system-packages
```

Note: The `--break-system-packages` flag is required on modern Raspberry Pi OS (Debian Trixie) to install Python packages system-wide, which is necessary for `sudo` to access them when running the display program.

### Running the Display Service

The display is controlled from a mobile-friendly website hosted by the Pi. Start it manually while developing:

```bash
sudo python3 main.py
```

Open `http://<pi-ip-address>:8080` from a device on the same trusted LAN. The service exposes no authentication or HTTPS, so do not expose this port to the public internet.

The UI lets you select a display mode, turn the panel on or off, adjust global brightness, and configure ambient-light automation. Image Viewer requires an explicit selection from the approved files in `res/`; uploads and arbitrary filesystem paths are intentionally not supported.

The service stores its runtime configuration in `neomatrix-config.json` next to the project. It records the selected mode, selected image asset, power state, brightness, and automation preferences. Set `NEOMATRIX_CONFIG` to use a different config path.

Available mode IDs are:

- `life`: Game of Life
- `spectrum`: Spectrum Analyzer (requires connected microphone)
- `image`: Image Viewer (requires selected asset)
- `thermal`: Thermal Camera
- `rain`: Pixel Rain
- `stars`: Pixel Stars
- `tetris`: Tetris AI
- `off`: Display Off

### Start at Boot with systemd

Copy the unit template and edit its two `/home/pi/pi-neomatrix` paths if this project is installed elsewhere:

```bash
sudo cp deploy/pi-neomatrix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pi-neomatrix
sudo systemctl status pi-neomatrix
```

The service runs as `root` because the current NeoPixel driver requires hardware privileges. Use `sudo systemctl restart pi-neomatrix` after deploying code changes, and `sudo journalctl -u pi-neomatrix -f` to follow logs.

### Ambient Light Automation

Connect the BH1750 over I²C. The service continues to run when the sensor is unavailable, and automation is disabled by default. From the UI settings page you can enable it and set sleep/wake lux thresholds, dwell times, brightness mapping, polling interval, and the manual override policy. By default it sleeps below 5 lux for 60 seconds, wakes above 10 lux for 15 seconds, and treats a manual change as a 30-minute override.

### Setting up the I2S Microphone
For the audio spectrum analyzer mode, configure your I2S MEMS microphone:
- https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test
- https://makersportal.com/shop/i2s-mems-microphone-for-raspberry-pi-inmp441
