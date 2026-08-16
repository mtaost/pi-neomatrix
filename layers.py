from PIL import Image, ImageEnhance


class SleepLayer:
    """Replaces the composed frame with black while the controller is asleep."""

    def apply(self, image, context):
        if context["sleeping"]:
            return Image.new("RGB", image.size, "black")
        return image


class BrightnessLayer:
    """Scales an RGB frame after all visual content has been composed."""

    def apply(self, image, context):
        brightness = context["brightness"]
        if brightness <= 0:
            return Image.new("RGB", image.size, "black")
        if brightness < 1:
            return ImageEnhance.Brightness(image).enhance(brightness)
        return image
