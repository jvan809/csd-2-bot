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
            "ocr_regions": {
                "current_recipe_name": {"top": 0, "left": 0, "width": 0, "height": 0},
                "current_ingredients": {"top": 0, "left": 0, "width": 0, "height": 0}
            },
            "bot_settings": {
                "tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe",
                "enable_failsafe": True,
                "panel_detection": {
                    "threshold_value": 245,
                    "min_area": 1000,
                    "min_aspect_ratio": 2.0,
                    "horizontal_gap_threshold": 30
                }
            },
            
            "controls": {
                "input_keys": ["A", "S", "D", "F", "Z", "X", "C", "V"],
                "confirm_key": "Enter"
            }
        }

    def _load_or_create_config(self):
        """Loads the configuration from the file, or creates it if it doesn't exist."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = self._get_default_config()
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

    def update_setting(self, section: str, key: str, value):
        """Updates a setting and saves the configuration."""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()

    def save_config(self):
        """Saves the current configuration to the file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)