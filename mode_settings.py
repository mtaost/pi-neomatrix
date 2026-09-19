import re


HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


SPECTRUM_SETTINGS = {
    "gain_db": {"type": "range", "label": "Input gain", "help": "Boost or reduce microphone sensitivity before the spectrum is calculated.", "min": -12, "max": 48, "step": 1, "default": 0, "unit": "dB"},
    "auto_gain": {"type": "boolean", "label": "Automatic gain", "help": "Continuously adjusts microphone sensitivity while preserving the manual gain value for later.", "default": False},
    "mirror_from_center": {"type": "boolean", "label": "Mirror from center", "help": "Draw each spectrum bar outward from the center line, mirrored above and below.", "default": False},
    "peak_markers": {"type": "boolean", "label": "Show peak markers", "help": "Hold the recent high point briefly, then let a white cap fall back toward the live bar.", "default": False},
    "palette": {"type": "select", "label": "Color palette", "help": "Choose the color treatment for spectrum bars.", "default": "classic", "choices": [{"value": "classic", "label": "Classic green / yellow / red"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "ocean", "label": "Ocean gradient"}, {"value": "sunset", "label": "Sunset gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "fixed_color": {"type": "color", "label": "Fixed spectrum color", "help": "Used when Color palette is set to Fixed color.", "default": "#00FF66"},
}


THERMAL_SETTINGS = {
    "refresh_rate": {"type": "select", "label": "Sensor refresh rate", "help": "Use a lower rate if the Pi reports frame retries or the image stays black. 4 Hz is a safe starting point.", "default": "4", "choices": [{"value": "2", "label": "2 Hz (most reliable)"}, {"value": "4", "label": "4 Hz (recommended)"}, {"value": "8", "label": "8 Hz"}, {"value": "16", "label": "16 Hz"}]},
    "exposure_mode": {"type": "select", "label": "Exposure method", "help": "Choose whether the palette follows the full frame, ignores temperature outliers, or uses a fixed range.", "default": "auto", "choices": [{"value": "auto", "label": "Auto min / max"}, {"value": "percentile", "label": "Percentile clipping"}, {"value": "fixed", "label": "Fixed temperature range"}]},
    "exposure_smoothing": {"type": "range", "label": "Exposure smoothing", "help": "Keep the color range steadier between frames. Lower values react faster to changes.", "min": 0, "max": 0.95, "step": 0.05, "default": 0.65},
    "min_temperature": {"type": "range", "label": "Minimum temperature", "help": "Lower end of the color range when Fixed temperature range is selected. Displayed in Fahrenheit.", "min": 5, "max": 35, "step": 0.5, "default": 20, "unit": "°F", "display_scale": 1.8, "display_offset": 32, "display_decimals": 1, "show_value": True},
    "max_temperature": {"type": "range", "label": "Maximum temperature", "help": "Upper end of the color range when Fixed temperature range is selected. Displayed in Fahrenheit.", "min": 15, "max": 45, "step": 0.5, "default": 30, "unit": "°F", "display_scale": 1.8, "display_offset": 32, "display_decimals": 1, "show_value": True},
    "low_percentile": {"type": "range", "label": "Low percentile", "help": "Ignore the coldest fraction of pixels when percentile clipping is selected.", "min": 0, "max": 45, "step": 1, "default": 5, "unit": "%"},
    "high_percentile": {"type": "range", "label": "High percentile", "help": "Ignore the hottest fraction of pixels when percentile clipping is selected.", "min": 55, "max": 100, "step": 1, "default": 95, "unit": "%"},
    "palette": {"type": "select", "label": "Thermal palette", "help": "Choose how temperature is translated into color.", "default": "ironbow", "choices": [{"value": "ironbow", "label": "Ironbow"}, {"value": "rainbow", "label": "Rainbow"}, {"value": "amber", "label": "Amber"}, {"value": "grayscale", "label": "Grayscale"}, {"value": "cool", "label": "Cool"}, {"value": "custom", "label": "Custom gradient"}]},
    "custom_cold_color": {"type": "color", "label": "Custom cold color", "help": "The color used at the low end of a custom thermal gradient.", "default": "#000020"},
    "custom_mid_color": {"type": "color", "label": "Custom middle color", "help": "The middle color in a custom thermal gradient.", "default": "#00A0FF"},
    "custom_hot_color": {"type": "color", "label": "Custom hot color", "help": "The color used at the high end of a custom thermal gradient.", "default": "#FFFF80"},
    "autorange": {"type": "boolean", "label": "Legacy automatic range", "help": "Compatibility setting for older saved thermal configurations.", "default": True, "hidden": True},
}


GAME_OF_LIFE_SETTINGS = {
    "iteration_delay": {"type": "range", "label": "Iteration speed", "help": "Higher values run faster.", "min": 0.02, "max": 1.0, "step": 0.01, "default": 0.05, "unit": "seconds", "inverse": True},
    "alive_color_mode": {"type": "select", "label": "Alive pixels", "help": "Choose a single shifting hue, a moving rainbow across living cells, or a fixed color.", "default": "rainbow_cycle", "choices": [{"value": "rainbow_cycle", "label": "Rainbow cycle"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "alive_fixed_color": {"type": "color", "label": "Fixed alive color", "help": "Used when Alive pixels is set to Fixed color.", "default": "#F00000"},
    "dead_color": {"type": "color", "label": "Dead pixel color", "help": "The background color for cells that are not alive.", "default": "#000000"},
    "rainbow_cycle_speed": {"type": "range", "label": "Rainbow cycle speed", "help": "Hue cycles per second for the single-color rainbow effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.25, "unit": "cycles/sec"},
    "rainbow_gradient_speed": {"type": "range", "label": "Rainbow gradient speed", "help": "Hue cycles per second for the rainbow gradient effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.15, "unit": "cycles/sec"},
}


PIXEL_RAIN_SETTINGS = {
    "palette": {"type": "select", "label": "Color palette", "help": "Choose the color treatment used by the falling drops.", "default": "ocean", "aliases": {"classic": "ocean"}, "choices": [{"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "ocean", "label": "Ocean gradient"}, {"value": "sunset", "label": "Sunset gradient"}, {"value": "twilight", "label": "Twilight purple / pink / blue"}, {"value": "fixed", "label": "Fixed color"}]},
    "fixed_color": {"type": "color", "label": "Fixed rain color", "help": "Used when Color palette is set to Fixed color.", "default": "#00BFFF"},
    "density": {"type": "range", "label": "Rain density", "min": 1, "max": 1000, "step": 1, "default": 150, "unit": "per 1,000"},
    "frame_delay": {"type": "range", "label": "Rain speed", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.04, "unit": "seconds", "inverse": True},
    "persistence": {"type": "range", "label": "Trail length", "min": 0.1, "max": 0.99, "step": 0.01, "default": 0.75},
    "trail_length_variance": {"type": "range", "label": "Trail length variance", "help": "Vary individual trail lengths by up to roughly 50% at the maximum.", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.0},
    "variable_drop_speed": {"type": "boolean", "label": "Variable drop speeds", "help": "Make individual drops fall at slightly different speeds while keeping their average speed unchanged.", "default": False},
    "drop_brightness_variance": {"type": "range", "label": "Per-drop brightness variance", "help": "Vary individual drop brightness by up to roughly 50% at the maximum.", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.0},
    # Kept hidden so existing saved configurations and API clients continue
    # to normalize successfully. PixelRain translates them to the palette
    # settings when no new palette is supplied.
    "rain_color_mode": {"type": "select", "label": "Legacy raindrop colors", "help": "Compatibility setting.", "default": "rainbow_cycle", "hidden": True, "choices": [{"value": "rainbow_cycle", "label": "Rainbow cycle"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "rain_fixed_color": {"type": "color", "label": "Legacy fixed raindrop color", "help": "Compatibility setting.", "default": "#00BFFF", "hidden": True},
    "rainbow_cycle_speed": {"type": "range", "label": "Legacy rainbow cycle speed", "help": "Compatibility setting.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.25, "unit": "cycles/sec", "hidden": True},
    "rainbow_gradient_speed": {"type": "range", "label": "Legacy rainbow gradient speed", "help": "Compatibility setting.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.15, "unit": "cycles/sec", "hidden": True},
}


PIXEL_STARS_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Higher values run faster.", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.03, "unit": "seconds", "inverse": True},
    "density": {"type": "range", "label": "Star density", "help": "The chance of a new star appearing in each pixel.", "min": 1, "max": 100000, "step": 1, "default": 5, "unit": "per 100,000"},
    "persistence": {"type": "range", "label": "Star persistence", "help": "Higher values keep stars visible for longer.", "min": 0.5, "max": 0.999, "step": 0.001, "default": 0.99},
    "burst_chance": {"type": "range", "label": "Burst frequency", "help": "The chance of a denser star burst on each frame.", "min": 0, "max": 100, "step": 1, "default": 1, "unit": "per 10,000"},
    "burst_density": {"type": "range", "label": "Burst density", "help": "The maximum star density during a burst.", "min": 1, "max": 100000, "step": 1, "default": 90, "unit": "per 100,000"},
    "star_color_mode": {"type": "select", "label": "Star colors", "help": "Choose a single shifting hue, a rainbow across the display, or a fixed color.", "default": "rainbow_cycle", "choices": [{"value": "rainbow_cycle", "label": "Rainbow cycle"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "star_fixed_color": {"type": "color", "label": "Fixed star color", "help": "Used when Star colors is set to Fixed color.", "default": "#FFFFFF"},
    "rainbow_cycle_speed": {"type": "range", "label": "Rainbow cycle speed", "help": "Hue cycles per second for the single-color rainbow effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.25, "unit": "cycles/sec"},
    "rainbow_gradient_speed": {"type": "range", "label": "Rainbow gradient speed", "help": "Hue cycles per second for the rainbow gradient effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.15, "unit": "cycles/sec"},
}


FIREWORKS_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Higher values animate faster.", "min": 0.02, "max": 0.2, "step": 0.01, "default": 0.05, "unit": "seconds", "inverse": True},
    "launch_rate": {"type": "range", "label": "Launch frequency", "help": "Average rocket launches per second.", "min": 0.05, "max": 2.0, "step": 0.05, "default": 0.35, "unit": "launches/sec"},
    "burst_size": {"type": "range", "label": "Burst size", "help": "Number of particles created when a rocket explodes.", "min": 8, "max": 64, "step": 1, "default": 26, "unit": "particles"},
    "trail_persistence": {"type": "range", "label": "Trail persistence", "help": "Higher values keep trails visible for longer.", "min": 0.1, "max": 0.95, "step": 0.01, "default": 0.7},
    "gravity": {"type": "range", "label": "Gravity", "help": "How strongly burst particles fall.", "min": 0.0, "max": 0.2, "step": 0.01, "default": 0.01},
    "launch_speed": {"type": "range", "label": "Launch speed", "help": "How quickly rockets rise before bursting.", "min": 0.4, "max": 2.0, "step": 0.05, "default": 1.0},
    "burst_speed": {"type": "range", "label": "Burst speed", "help": "How quickly explosion particles spread.", "min": 0.2, "max": 2.0, "step": 0.05, "default": 0.8},
    "fade_to_color": {"type": "boolean", "label": "Fade fragments to another color", "help": "Each burst transitions uniformly to a different palette color as it fades.", "default": False},

    "palette": {"type": "select", "label": "Palette", "help": "Choose a curated collection of firework colors.", "default": "classic", "choices": [{"value": "classic", "label": "Classic"}, {"value": "warm", "label": "Warm"}, {"value": "cool", "label": "Cool"}, {"value": "patriotic", "label": "Patriotic"}, {"value": "neon", "label": "Neon"}]},
}


FIREPLACE_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "How often the flame is redrawn.", "min": 0.02, "max": 0.2, "step": 0.01, "default": 0.05, "unit": "seconds", "inverse": True},
    "flame_height": {"type": "range", "label": "Flame height", "help": "The maximum height reached by the flames.", "min": 0.45, "max": 1.0, "step": 0.01, "default": 0.9},
    "flame_scale": {"type": "range", "label": "Flame shape scale", "help": "Lower values make broad tongues; higher values create smaller, more active tongues.", "min": 0.05, "max": 0.5, "step": 0.01, "default": 0.18, "unit": "detail"},
    "flicker": {"type": "range", "label": "Flicker", "help": "How much the flame edge dances and changes shape.", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.75},
    "turbulence": {"type": "range", "label": "Turbulence", "help": "Blend in finer noise to create more irregular flame movement.", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.55},
    "ember_density": {"type": "range", "label": "Ember density", "help": "How frequently glowing embers rise from the logs.", "min": 0, "max": 100, "step": 1, "default": 18, "unit": "%"},
    "palette": {"type": "select", "label": "Color palette", "help": "Choose a curated fire treatment or define your own three-color gradient.", "default": "classic", "choices": [{"value": "classic", "label": "Classic fire"}, {"value": "hearth", "label": "Hearth"}, {"value": "candle", "label": "Candlelight"}, {"value": "blue_flame", "label": "Blue flame"}, {"value": "neon", "label": "Neon fire"}, {"value": "custom", "label": "Custom gradient"}]},
    "custom_shadow_color": {"type": "color", "label": "Custom shadow color", "help": "The darkest color in the custom flame gradient.", "default": "#160000"},
    "custom_mid_color": {"type": "color", "label": "Custom middle color", "help": "The middle color in the custom flame gradient.", "default": "#FF4200"},
    "custom_highlight_color": {"type": "color", "label": "Custom highlight color", "help": "The hottest color in the custom flame gradient.", "default": "#FFF2A1"},
}


TETRIS_SETTINGS = {
    "animation_speed": {"type": "range", "label": "Animation speed", "help": "Higher values animate faster.", "min": 0.02, "max": 0.375, "step": 0.01, "default": 0.08, "unit": "seconds", "inverse": True},
    "strategy": {"type": "select", "label": "AI strategy", "help": "Changing strategy starts a fresh game.", "default": "balanced", "choices": [{"value": "balanced", "label": "Balanced"}, {"value": "fast", "label": "Fast"}, {"value": "perfect_clear", "label": "Perfect Clear"}]},
    "simulated_garbage": {"type": "boolean", "label": "Simulate garbage", "help": "Add grey garbage rows between pieces.", "default": False},
    "garbage_frequency": {"type": "range", "label": "Garbage frequency", "help": "Higher values add garbage more often: 1 is one row every 10 locks; 10 is one row every lock.", "min": 1, "max": 10, "step": 1, "default": 1, "unit": "frequency"},
    "garbage_lines": {"type": "range", "label": "Garbage lines", "help": "Rows added at each garbage event.", "min": 1, "max": 6, "step": 1, "default": 1, "unit": "rows"},
    "garbage_messiness": {"type": "range", "label": "Garbage messiness", "help": "Chance that the hole moves to a new column on the next garbage row.", "min": 0, "max": 100, "step": 1, "default": 30, "unit": "%"},
}


PERLIN_NOISE_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Higher values update the gradient more often.", "min": 0.02, "max": 0.2, "step": 0.01, "default": 0.05, "unit": "seconds", "inverse": True},
    "speed": {"type": "range", "label": "Noise movement", "help": "How quickly the noise field drifts across the display.", "min": 0.0, "max": 1.0, "step": 0.01, "default": 0.15, "unit": "cells/sec"},
    "scale": {"type": "range", "label": "Noise scale", "help": "Lower values make broader, slower-changing shapes; higher values add finer detail.", "min": 0.05, "max": 0.5, "step": 0.01, "default": 0.16, "unit": "detail"},
    "octaves": {"type": "range", "label": "Noise layers", "help": "Number of detail layers blended into the gradient.", "min": 1, "max": 5, "step": 1, "default": 3, "unit": "layers"},
    "persistence": {"type": "range", "label": "Detail persistence", "help": "How strongly each finer noise layer contributes to the result.", "min": 0.25, "max": 0.85, "step": 0.01, "default": 0.5},
    "contrast": {"type": "range", "label": "Gradient contrast", "help": "Stretch or soften the transition between palette colors.", "min": 0.5, "max": 2.0, "step": 0.05, "default": 1.0},
    "palette": {"type": "select", "label": "Color palette", "help": "Choose a curated color treatment or define your own three-color gradient.", "default": "aurora", "choices": [{"value": "aurora", "label": "Aurora"}, {"value": "ocean", "label": "Ocean"}, {"value": "sunset", "label": "Sunset"}, {"value": "ember", "label": "Ember"}, {"value": "neon", "label": "Neon"}, {"value": "custom", "label": "Custom gradient"}]},
    "custom_start_color": {"type": "color", "label": "Custom shadow color", "help": "The darkest color in the custom gradient.", "default": "#05001A"},
    "custom_mid_color": {"type": "color", "label": "Custom middle color", "help": "The middle color in the custom gradient.", "default": "#005B7F"},
    "custom_end_color": {"type": "color", "label": "Custom highlight color", "help": "The brightest color in the custom gradient.", "default": "#B7FF5A"},
}


CITYSCAPE_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "How often the cityscape is redrawn.", "min": 0.02, "max": 0.2, "step": 0.01, "default": 0.05, "unit": "seconds", "inverse": True},
    "scroll_speed": {"type": "range", "label": "Scroll speed", "help": "How quickly the skyline travels from right to left.", "min": 0.0, "max": 8.0, "step": 0.1, "default": 1.2, "unit": "cells/sec"},
    "sky_mode": {"type": "select", "label": "Sky cycle", "help": "Loop through day, sunset, and night, or hold one time of day.", "default": "cycle", "choices": [{"value": "cycle", "label": "Automatic day / sunset / night"}, {"value": "day", "label": "Day"}, {"value": "sunset", "label": "Sunset"}, {"value": "night", "label": "Night"}]},
    "cycle_duration": {"type": "range", "label": "Cycle duration", "help": "Length of one complete day-to-night loop when Sky cycle is automatic.", "min": 20, "max": 3600, "step": 10, "default": 180, "unit": "seconds"},
    "building_height": {"type": "range", "label": "Building height", "help": "Controls the tallest foreground buildings relative to the panel height.", "min": 0.35, "max": 0.9, "step": 0.05, "default": 0.65},
    "window_density": {"type": "range", "label": "Lit windows", "help": "The portion of windows that glow after dark.", "min": 0, "max": 100, "step": 1, "default": 42, "unit": "%"},
}

def default_settings(schema):
    return {key: field["default"] for key, field in schema.items()}


def hex_to_rgb(value):
    if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
        raise ValueError("Color must be a #RRGGBB value.")
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))

def normalize_settings(schema, values=None, base=None):
    if values is None:
        values = {}
    if not isinstance(values, dict):
        raise ValueError("Mode settings must be an object.")
    unknown = set(values) - set(schema)
    if unknown:
        raise ValueError(f"Unknown mode setting: {sorted(unknown)[0]}")
    result = default_settings(schema)
    if base:
        result.update({key: base[key] for key in schema if key in base})
    for key, value in values.items():
        field = schema[key]
        field_type = field["type"]
        if field_type == "select":
            choices = {choice["value"] for choice in field["choices"]}
            aliases = field.get("aliases", {})
            if value in aliases:
                value = aliases[value]
            if value not in choices:
                raise ValueError(f"{field['label']} is invalid.")
            result[key] = value
            continue
        if field_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"{field['label']} must be a boolean.")
            result[key] = value
            continue

        if field_type == "color":
            if not isinstance(value, str) or not HEX_COLOR.fullmatch(value):
                raise ValueError(f"{field['label']} must be a #RRGGBB color.")
            result[key] = value.upper()
            continue
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field['label']} must be numeric.") from error
        if not field["min"] <= number <= field["max"]:
            raise ValueError(f"{field['label']} must be from {field['min']} to {field['max']}.")
        result[key] = number
    return result
