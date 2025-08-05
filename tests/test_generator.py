import logging
import json
from pathlib import Path
import time
from datetime import datetime
from pynput import keyboard
import pyautogui
import sys

# Add project root to the Python path to allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ocr_processor import OcrProcessor
from src.config_manager import ConfigManager
from src.logger_setup import setup_logger

log = logging.getLogger('csd2_bot')


class TestGenerator:
    """
    A tool to semi-automatically generate test cases for the bot's matching logic.

    It works by listening to user key presses during gameplay to capture the
    "ground truth" for a recipe, creating a structured test file for each
    page of ingredients.
    """
    def __init__(self, ocr_processor: OcrProcessor, config_manager: ConfigManager):

        self.ocr = ocr_processor
        self.config = config_manager
        self.is_running = False
        self.listener = None
        self.is_aborted = False

        # --- Captured Data ---
        self.full_recipe_steps = []
        self.ingredient_pages_ocr = []
        self.key_presses_per_page = []

        # --- Configured Keys ---
        self.page_turn_key = self.config.get_setting("controls.page_turn_key")
        self.confirm_key = self.config.get_setting("controls.confirm_key")
        self.undo_key = 'backspace' # Hardcoded for now, could be configurable

        # --- Trigger Config ---
        trigger_config = self.config.get_setting("bot_settings.recipe_trigger")
        self.trigger_x = trigger_config.get("check_pixel_x")
        self.trigger_y = trigger_config.get("check_pixel_y")
        self.expected_color = tuple(trigger_config.get("expected_color_rgb"))
        self.tolerance = trigger_config.get("tolerance", 10)
        self.loop_delay = self.config.get_setting("bot_settings.main_loop_delay", default=1.0)

    def _reset_capture(self):
        """Resets all captured data for a new session."""
        self.full_recipe_steps = []
        self.ingredient_pages_ocr = []  
        self.key_presses_per_page = [[]] # Start with one empty page 
        self.is_aborted = False
        log.info("Test generator state has been reset.")

    def start_capture(self):
        """Starts the test generation process."""
        self._reset_capture()
        log.info("--- Starting Test Case Capture ---")
        log.info(f"Press '{self.confirm_key}' to finish, '{self.page_turn_key}' to turn page, '{self.undo_key}' to undo last key.")

        # 1. Initial OCR
        recipe_roi = self.config.get_setting("ocr_regions.recipe_list_roi")
        panel_roi = self.config.get_setting("ocr_regions.ingredient_panel_roi")
        slot_rois = self.config.get_setting("ocr_regions.ingredient_slot_rois")

        self.full_recipe_steps = self.ocr.process_recipe_list_roi(recipe_roi)
        page_1_ingredients = self.ocr.process_ingredient_panel_roi(panel_roi, slot_rois)
        self.ingredient_pages_ocr.append(page_1_ingredients)

        log.info(f"Captured initial recipe: {self.full_recipe_steps}")
        log.info(f"Captured page 1 ingredients: {page_1_ingredients}")

        # 2. Start Listener
        self.is_running = True
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()
        self.listener.join() # Blocks until listener is stopped

        log.info("--- Capture Finished ---")
        self._generate_test_files()

    def _wait_for_recipe_trigger(self):
        """Waits for the pixel color that indicates a new recipe is available."""
        log.info("Waiting for a new recipe to start capture...")
        while not pyautogui.pixelMatchesColor(self.trigger_x, self.trigger_y, self.expected_color, tolerance=self.tolerance):
            time.sleep(self.loop_delay)
        log.info("Recipe trigger detected. Starting capture process.")

    def run_loop(self):
        """Main loop for the test generator."""
        log.info("Test Generator is running. Press Ctrl+C in the console to exit.")
        if self.config.get_setting("bot_settings.enable_failsafe", default=True):
            pyautogui.FAILSAFE = True
            log.info("PyAutoGUI failsafe enabled. Move mouse to top-left corner to stop.")
        else:
            pyautogui.FAILSAFE = False
            log.warning("PyAutoGUI failsafe is disabled.")

        while True:
            try:
                pyautogui.sleep(self.loop_delay)
                self._wait_for_recipe_trigger()
                self.start_capture()
                log.info("Capture session finished. Looping back to wait for next recipe.")
            except pyautogui.FailSafeException:
                log.info("Failsafe triggered. Stopping test generator.")
                break # Exit the loop

    def _on_press(self, key):
        """Callback function for the pynput listener."""
        try:
            key_name = key.char.lower() if hasattr(key, 'char') and key.char else key.name
        except AttributeError:
            key_name = key.name

        if not self.is_running:
            return False

        log.debug(f"Key pressed: {key_name}")

        if key_name == self.confirm_key:
            self.is_running = False
            return False # Stop the listener

        if key_name == self.page_turn_key:
            log.info("Page turn detected. Capturing next ingredient panel.")
            self.key_presses_per_page.append([]) # Add a new page for keys
            # Give game time to animate page turn
            time.sleep(self.config.get_setting("bot_settings.page_delay", 0.25))
            
            panel_roi = self.config.get_setting("ocr_regions.ingredient_panel_roi")
            slot_rois = self.config.get_setting("ocr_regions.ingredient_slot_rois")
            next_page_ingredients = self.ocr.process_ingredient_panel_roi(panel_roi, slot_rois)
            self.ingredient_pages_ocr.append(next_page_ingredients)
            log.info(f"Captured new page ingredients: {next_page_ingredients}")

        elif key_name == self.undo_key:
            self.is_aborted = True
            self.is_running = False
            return False
        
        else:
            # Assume it's an ingredient key
            # We only care about single character keys for ingredients
            if len(key_name) == 1:
                self.key_presses_per_page[-1].append(key_name.upper())
                log.info(f"Captured key: {key_name.upper()}")

    def _generate_test_files(self):
        """Processes captured data and saves it into structured JSON files."""
        if self.is_aborted:
            log.info("Test case generation aborted by user. No files will be saved.")
            pyautogui.sleep(3)
            return

        if not self.full_recipe_steps:
            log.warning("No recipe steps were captured. Cannot generate test files.")
            return

        log.info("Generating test files...")

        # Create a unique directory for this test run based on the recipe name and timestamp
        first_step = self.full_recipe_steps[0] if self.full_recipe_steps else "unknown"
        # Sanitize recipe name for use in a directory path
        sanitized_name = "".join(c for c in first_step if c.isalnum() or c in " _-").rstrip().replace(" ", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        test_run_dir = Path(f"tests/fixtures/generated/{sanitized_name}_{timestamp}")
        try:
            test_run_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Saving test files to: {test_run_dir}")
        except OSError as e:
            log.error(f"Failed to create test directory {test_run_dir}. Error: {e}")
            return

        for i, (page_ingredients, page_keys) in enumerate(zip(self.ingredient_pages_ocr, self.key_presses_per_page)):
            page_num = i + 1
            is_last_page = page_num == len(self.ingredient_pages_ocr)
            # For the current page, the required steps are the remainder of the full list

            test_case_data = {
                "description": f"Test case for '{first_step}', page {page_num}",
                "input": {
                    "recipe_steps": self.full_recipe_steps[i] + (self.full_recipe_steps[3] if is_last_page else []),
                    "available_on_page": page_ingredients
                },
                "expected": {"keys_to_press": page_keys}
                # note: expected keys to press might be an empty list - the bot not firing is just as important as the bot firing
            }

            file_path = test_run_dir / f"test_page_{page_num}.json"
            with open(file_path, 'w') as f:
                json.dump(test_case_data, f, indent=4)
            log.info(f"Successfully generated test file: {file_path}")

            # Update the count of processed steps for the next iteration

if __name__ == "__main__":
    config_manager = ConfigManager()
    # Setup logger using the config
    setup_logger(config_manager)

    ocr = OcrProcessor(config_manager)
    test_generator = TestGenerator(ocr, config_manager)

    try:
        test_generator.run_loop()
    except KeyboardInterrupt:
        log.info("\nTest generator stopped by user (Ctrl+C).")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        log.info("Test generator shutting down.")
