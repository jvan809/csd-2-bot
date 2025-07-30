import json
from pathlib import Path

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
                    "min_aspect_ratio": 2.0
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

    def get_setting(self, section: str, key: str):
        """Retrieves a specific setting from the configuration."""
        return self.config.get(section, {}).get(key)

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