import re


HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


GAME_OF_LIFE_SETTINGS = {
    "iteration_delay": {"type": "range", "label": "Iteration speed", "help": "Seconds between generations. Lower values run faster.", "min": 0.02, "max": 1.0, "step": 0.01, "default": 0.05, "unit": "seconds"},
    "alive_color_mode": {"type": "select", "label": "Alive pixels", "help": "Choose a single shifting hue, a moving rainbow across living cells, or a fixed color.", "default": "rainbow_cycle", "choices": [{"value": "rainbow_cycle", "label": "Rainbow cycle"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "alive_fixed_color": {"type": "color", "label": "Fixed alive color", "help": "Used when Alive pixels is set to Fixed color.", "default": "#F00000"},
    "dead_color": {"type": "color", "label": "Dead pixel color", "help": "The background color for cells that are not alive.", "default": "#000000"},
    "rainbow_cycle_speed": {"type": "range", "label": "Rainbow cycle speed", "help": "Hue cycles per second for the single-color rainbow effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.25, "unit": "cycles/sec"},
    "rainbow_gradient_speed": {"type": "range", "label": "Rainbow gradient speed", "help": "Hue cycles per second for the rainbow gradient effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.15, "unit": "cycles/sec"},
}


PIXEL_RAIN_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Seconds between rain updates. Lower values run faster.", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.04, "unit": "seconds"},
    "density": {"type": "range", "label": "Rain density", "help": "The chance of a new drop appearing in each column.", "min": 1, "max": 1000, "step": 1, "default": 30, "unit": "per 1,000"},
    "persistence": {"type": "range", "label": "Trail persistence", "help": "Higher values keep each raindrop trail visible for longer.", "min": 0.1, "max": 0.99, "step": 0.01, "default": 0.75},
    "rain_color_mode": {"type": "select", "label": "Raindrop colors", "help": "Choose a single shifting hue, a rainbow across columns, or a fixed color.", "default": "rainbow_cycle", "choices": [{"value": "rainbow_cycle", "label": "Rainbow cycle"}, {"value": "rainbow_gradient", "label": "Rainbow gradient"}, {"value": "fixed", "label": "Fixed color"}]},
    "rain_fixed_color": {"type": "color", "label": "Fixed raindrop color", "help": "Used when Raindrop colors is set to Fixed color.", "default": "#00BFFF"},
    "rainbow_cycle_speed": {"type": "range", "label": "Rainbow cycle speed", "help": "Hue cycles per second for the single-color rainbow effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.25, "unit": "cycles/sec"},
    "rainbow_gradient_speed": {"type": "range", "label": "Rainbow gradient speed", "help": "Hue cycles per second for the rainbow gradient effect.", "min": 0.0, "max": 2.0, "step": 0.01, "default": 0.15, "unit": "cycles/sec"},
}


PIXEL_STARS_SETTINGS = {
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Seconds between star updates. Lower values run faster.", "min": 0.01, "max": 0.2, "step": 0.01, "default": 0.03, "unit": "seconds"},
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
    "frame_delay": {"type": "range", "label": "Animation speed", "help": "Seconds between frames. Lower values animate faster.", "min": 0.02, "max": 0.2, "step": 0.01, "default": 0.05, "unit": "seconds"},
    "launch_rate": {"type": "range", "label": "Launch frequency", "help": "Average rocket launches per second.", "min": 0.05, "max": 2.0, "step": 0.05, "default": 0.35, "unit": "launches/sec"},
    "burst_size": {"type": "range", "label": "Burst size", "help": "Number of particles created when a rocket explodes.", "min": 8, "max": 64, "step": 1, "default": 26, "unit": "particles"},
    "trail_persistence": {"type": "range", "label": "Trail persistence", "help": "Higher values keep trails visible for longer.", "min": 0.1, "max": 0.95, "step": 0.01, "default": 0.7},
    "gravity": {"type": "range", "label": "Gravity", "help": "How strongly burst particles fall.", "min": 0.0, "max": 0.2, "step": 0.01, "default": 0.01},
    "launch_speed": {"type": "range", "label": "Launch speed", "help": "How quickly rockets rise before bursting.", "min": 0.4, "max": 2.0, "step": 0.05, "default": 1.0},
    "burst_speed": {"type": "range", "label": "Burst speed", "help": "How quickly explosion particles spread.", "min": 0.2, "max": 2.0, "step": 0.05, "default": 0.8},
    "fade_to_color": {"type": "boolean", "label": "Fade fragments to another color", "help": "Each burst transitions uniformly to a different palette color as it fades.", "default": False},

    "palette": {"type": "select", "label": "Palette", "help": "Choose a curated collection of firework colors.", "default": "classic", "choices": [{"value": "classic", "label": "Classic"}, {"value": "warm", "label": "Warm"}, {"value": "cool", "label": "Cool"}, {"value": "patriotic", "label": "Patriotic"}, {"value": "neon", "label": "Neon"}]},
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
            if value not in {choice["value"] for choice in field["choices"]}:
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

