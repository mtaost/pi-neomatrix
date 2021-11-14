# pi-neomatrix
multipurpose LED display driven by raspberry pi
# Features
# Setup
## Hardware ##
Raspberry Pi 3 B+
HW-221 Level shifter
16x16 WS2812 matrix


## Sofware ##
OS: Raspian OS Lite server, enable ssh, I2C, SPI, GPIO, docker

Numpy for raspberry pi
sudo apt-get install libopenjp2-7

pyaudio
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

https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test

