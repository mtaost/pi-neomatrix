from display_modes import module
from PIL import Image
import time

class ImageViewer(module.Module):
    """shrek is love"""

    def __init__(self, driver, filename):
        super().__init__(driver)
        self.filename = filename

    def run(self):
        with Image.open(self.filename) as img:
            needs_conversion = img.mode != 'RGB'
            # print("needs conversion" + str(img.mode))
            needs_resize = img.size != (self.width, self.height)
            # print("needs resize" + str(needs_resize))
            if img.is_animated:
                frame = 0
                while not self.should_stop():
                    try:
                        start_time = time.time()
                        img.seek(frame)
                        self.image = img
                        if needs_conversion:
                            self.image = img.convert('RGB')
                        if needs_resize:
                            self.image = self.image.resize((self.width,self.height))
                        self.display()
                        wait_time = self.image.info['duration']/1000 - time.time() + start_time
                        if wait_time > 0 and not self.wait(wait_time):
                            break
                        frame += 1
                    except EOFError:
                        frame = 0
                        continue
            else:
                self.image = img
                if needs_conversion:
                    self.image = img.convert('RGB')
                if needs_resize:
                    self.image = img.resize((self.width,self.height))
                self.display()