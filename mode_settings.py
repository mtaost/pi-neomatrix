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

