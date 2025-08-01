import pyautogui
import pydirectinput
from src.logger_setup import setup_logger
from src.config_manager import ConfigManager
from src.input_handler import press_key
from src.ocr_processor import OcrProcessor
from src.bot_logic import map_ingredients_to_keys
import logging

class CSD2Bot:
    def __init__(self, config_manager: ConfigManager, ocr_processor: OcrProcessor):
        self.log = logging.getLogger('csd2_bot')
        self.config_manager = config_manager
        self.ocr = ocr_processor

        # --- Load Config Settings ---
        self.recipe_roi = self.config_manager.get_setting("ocr_regions.recipe_list_roi")
        self.panel_roi = self.config_manager.get_setting("ocr_regions.ingredient_panel_roi")
        self.input_keys = self.config_manager.get_setting("controls.input_keys")
        self.page_turn_key = self.config_manager.get_setting("controls.page_turn_key")
        self.confirm_key = self.config_manager.get_setting("controls.confirm_key")
        self.loop_delay = self.config_manager.get_setting("bot_settings.main_loop_delay", default=1.0)
        
        trigger_config = self.config_manager.get_setting("bot_settings.recipe_trigger")
        self.trigger_x = trigger_config.get("check_pixel_x")
        self.trigger_y = trigger_config.get("check_pixel_y")
        self.expected_color = tuple(trigger_config.get("expected_color_rgb"))
        self.tolerance = trigger_config.get("tolerance", 10)

    def run(self):
        """Main bot loop. Waits for a recipe and processes it."""
        self.log.info(f"Waiting for a new recipe. Loop delay: {self.loop_delay}s")
        self._wait_for_recipe_trigger()

        self.log.debug(f"Recipe trigger detected at ({self.trigger_x}, {self.trigger_y}). Reading recipe...")
        remaining_steps = self.ocr.process_recipe_list_roi(self.recipe_roi)

        if not remaining_steps:
            self.log.warning("Recipe card detected, but failed to read any recipe text. Skipping this attempt.")
            return

        self.log.info(f"New recipe detected! Steps: {remaining_steps}")
        self._process_recipe(remaining_steps)

    def _wait_for_recipe_trigger(self):
        """Waits for the pixel color that indicates a new recipe is available."""
        while not pyautogui.pixelMatchesColor(self.trigger_x, self.trigger_y, self.expected_color, tolerance=self.tolerance):
            pyautogui.sleep(self.loop_delay)

    def _process_recipe(self, remaining_steps: list):
        """Processes all ingredients for the current recipe, turning pages as needed."""
        page_turns = 0
        max_page_turns = 2  # Initial page + 2 turns

        while remaining_steps and page_turns <= max_page_turns:
            self.log.debug(f"Processing page {page_turns + 1}. Remaining steps: {remaining_steps}")

            available_on_page = self.ocr.process_ingredient_panel_roi(self.panel_roi)
            self.log.info(f"Available on page: {available_on_page}")

            keys_to_press, matched_ingredients = map_ingredients_to_keys(remaining_steps, available_on_page, self.input_keys)
            self.log.info(f"Matched ingredients: {matched_ingredients}. Keys to press: {keys_to_press}")

            if keys_to_press:
                for key in keys_to_press:
                    press_key(key)

                # Remove matched ingredients (no duplicates is guarenteed by the game)
                temp_matched = list(matched_ingredients)
                remaining_steps = [step for step in remaining_steps if not (step in temp_matched)]

            if remaining_steps and page_turns < max_page_turns:
                self.log.debug("There are remaining steps, turning page.")
                press_key(self.page_turn_key)
                page_turns += 1
            else:
                break  # No more steps or max pages reached

        self._serve_order(remaining_steps)

    def _serve_order(self, remaining_steps: list):
        """Presses the confirm key if the recipe is complete, otherwise logs a warning."""
        if not remaining_steps:
            self.log.info("Recipe complete. Pressing confirm key.")
            press_key(self.confirm_key)
        else:
            self.log.warning(f"Finished recipe attempt with remaining steps: {remaining_steps}. Manual intervention may be needed.")
            pyautogui.sleep(5)

def main():      
    """Main application entry point."""
    # 1. Create config manager first, as it's needed by the logger
    config_manager = ConfigManager()

    # 2. Setup logger using the config
    log = setup_logger(config_manager)

    # 3. Configure Tesseract now that the logger is ready
    ocr_processor = OcrProcessor(config_manager)

    # --- Configure Input Library ---
    # Lower the default pause in pydirectinput for faster key presses.
    # A small pause can sometimes be more reliable than 0 for some applications.
    key_delay = config_manager.get_setting("bot_settings.key_delay", default=0.05)
    pydirectinput.PAUSE = key_delay

    log.info("Starting CSD2 Bot...")
    
    # Enable PyAutoGUI failsafe
    if config_manager.get_setting("bot_settings.enable_failsafe", default=True):
        pyautogui.FAILSAFE = True
        log.info("PyAutoGUI failsafe enabled. Move mouse to top-left corner to stop.")
    else:
        pyautogui.FAILSAFE = False
        log.warning("PyAutoGUI failsafe is disabled.")
        
    bot = CSD2Bot(config_manager, ocr_processor)

    try:
        log.info("Bot is running. Press Ctrl+C in the console to exit.")
        while True:
            bot.run() # delay is in this function so no need for sleep here

    except KeyboardInterrupt:
        log.info("Bot stopped by user (Ctrl+C).")
    except pyautogui.FailSafeException:
        log.info("Bot stopped by user (Failsafe triggered).")
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        log.info("CSD2 Bot shutting down.")

if __name__ == "__main__":
    main()