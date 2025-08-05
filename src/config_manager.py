import json
from pathlib import Path
import logging

log = logging.getLogger('csd2_bot')


class ConfigManager:
    """Manages loading and saving of the application's configuration file."""

    def __init__(self, config_path: str = 'config.json'):
        self.config_path = Path(config_path)
        self.config = {}
        self._load_or_create_config()

    def _get_default_config(self) -> dict:
        """Returns the default configuration structure."""
        return {
            "ocr_regions": { # This structure is updated by setup.py or manual config
                "recipe_list_roi": {"top": 0, "left": 0, "width": 0, "height": 0},
                "ingredient_panel_roi": {"top": 0, "left": 0, "width": 0, "height": 0},
                "ingredient_slot_rois" : None
            },
            "recipe_layout": {
                "page_indicators": None,
                "recipe_slot_rois": None,
                "vertical_coords": None
            },
            "bot_settings": {
                "tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe",
                "ingredient_mask_path": "",
                "enable_failsafe": True,
                "panel_detection": {
                    "threshold_value": 245,
                    "min_area": 1000,
                    "min_aspect_ratio": 2.0,
                    "horizontal_gap_threshold": 30
                },
                "recipe_trigger": {
                    "check_pixel_x": 454,
                    "check_pixel_y": 973,
                    "expected_color_rgb": [54, 54, 54],
                    "tolerance": 10
                },
                "ocr_upscale_factor": 2.0,
                "right_panel_shear_factor": 0.14,
                "min_confidence": 50,
                "logging_level": "INFO",
                "main_loop_delay": 1.0,
                "key_delay": 0.05,
                "page_delay": 0.25,
                "fuzzy_matching_enabled": True,
                "multi_step_char_threshold": 20,
                "fuzzy_match_threshold": 0.6
            },
            
            "controls": {
                "input_keys": ["A", "S", "D", "F", "Z", "X", "C", "V"],
                "confirm_key": "enter",
                "page_turn_key": "space"
            }
        }

    def _merge_dicts(self, base_dict: dict, override_dict: dict) -> dict:
        """
        Recursively merges the override_dict into the base_dict.
        Values from override_dict take precedence. This ensures user settings
        are preserved while new default settings can be added.
        """
        merged = base_dict.copy()
        for key, value in override_dict.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _load_or_create_config(self):
        """
        Loads config from file, or creates it if it doesn't exist.
        Merges with default config to ensure all keys are present.
        """
        default_config = self._get_default_config()
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                self.config = self._merge_dicts(default_config, user_config)
            except (json.JSONDecodeError, TypeError):
                log.warning(f"Could not parse '{self.config_path}'. Using default config.")
                self.config = default_config
        else:
            self.config = default_config
        self.save_config()

    def get_setting(self, path: str, default=None):
        """
        Retrieves a nested setting from the configuration using a dot-separated path.
        e.g., get_setting("bot_settings.panel_detection.min_area")

        Args:
            path: The dot-separated path to the setting.
            default: The value to return if the setting is not found.

        Returns:
            The value of the setting, or the default value if not found.
        """
        keys = path.split('.')
        value = self.config
        for key in keys:
            value = value.get(key)
            if value is None:
                log.warning(f"Setting '{path}' not found in configuration. Using default value: {default}")
                return default
        return value

    def update_setting(self, path: str, value):
        """
        Updates a nested setting in the configuration using a dot-separated path
        and saves the configuration.
        e.g., update_setting("bot_settings.panel_detection.min_area", 1200)

        Args:
            path: The dot-separated path to the setting.
            value: The new value to set.
        """
        keys = path.split('.')
        if not keys or not keys[0]:
            log.error("Cannot update setting with an empty or invalid path.")
            return

        current_level = self.config
        for key in keys[:-1]:
            current_level = current_level.setdefault(key, {})
            if not isinstance(current_level, dict):
                log.error(f"Cannot update setting '{path}'. Part of the path ('{key}') is not a dictionary.")
                return

        current_level[keys[-1]] = value
        self.save_config()

    def save_config(self):
        """Saves the current configuration to the file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)