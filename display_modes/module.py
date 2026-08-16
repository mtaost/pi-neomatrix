from PIL import Image
import threading
import time


class Module:
    """Base class for cooperative display modes.

    A mode draws into ``self.image`` and calls ``display``.  The controller
    installs a frame sink so only its compositor writes to the LED hardware.
    """

    def __init__(self, driver):
        self.width = driver.width
        self.height = driver.height
        self.driver = driver
        self.frame_sink = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.image = Image.new("RGB", (self.width, self.height), "black")
        self.pixels = self.image.load()

    def display(self):
        if self.should_stop():
            return False
        self.wait_until_resumed()
        if self.should_stop():
            return False
        if self.frame_sink:
            self.frame_sink(self.image.copy())
        else:
            self.driver.display(self.image)
        return True

    def should_stop(self):
        return self.stop_event.is_set()

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.should_stop():
            self.wait_until_resumed()
            if self.should_stop():
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            self.stop_event.wait(min(remaining, 0.1))
        return False

    def wait_until_resumed(self):
        while self.pause_event.is_set() and not self.should_stop():
            self.stop_event.wait(0.1)

    def run(self):
        while not self.should_stop():
            self.wait(0.1)

    def cleanup(self):
        return None
