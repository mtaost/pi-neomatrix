# pi-neomatrix
multipurpose LED display driven by raspberry pi
# Features
## Hardware Setup##
Required hardware:

- Raspberry Pi 3 B+
- HW-221 Level shifter
- 16x16 WS2812 matrix
- INMP441 I2S MEMS Microphone
- BH1750 Light sensor 

## Sofware Setup ##
To get started, set up a Raspberry Pi using the Raspian lite OS and connect it to your network using `raspiconfig`. In raspiconfig, go to interface and enable SSH, I2C, and SPI. 

Run `sudo apt-get update` to update the OS and then ensure SSH access before disconnecting the Raspberry Pi from your display. 

Numpy for raspberry pi
sudo apt-get install libopenjp2-7

Setting up the I2S microphone:
https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test

Installing pyaudio:
install portaudio through website
sudo apt-get install python3-dev
sudo git clone http://people.csail.mit.edu/hubert/git/pyaudio.git
sudo apt-get install libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev
What you need to do:

Uninstall python-pyaudio with sudo apt-get purge --remove python-pyaudio if you have it (This is version 0.2.8)
Download the latest version (19) of PortAudio.
Untar and install PortAudio
./configure
make
make install
Get the dependencies for pyaudio
portaudio19-dev
python-all-dev (python3-all-dev for Python 3)
sudo pip install pyaudio
After that, I was able to use pyaudio.

Pillow

