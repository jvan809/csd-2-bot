import pyautogui
import pydirectinput
import cv2
import logging
from src.logger_setup import setup_logger
from src.config_manager import ConfigManager
from src.input_handler import press_key, hold_key
from src.ocr_processor import OcrProcessor
from src.bot_logic import fuzzy_map_ingredients_to_keys
from src.screen_capture import capture_region

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
        self.page_delay = self.config_manager.get_setting("bot_settings.page_delay", default=0.25)
        self.page_indicators = self.config_manager.get_setting("recipe_layout.page_indicators")
        self.ingredient_slots = self.config_manager.get_setting("ocr_regions.ingredient_slot_rois")
        self.fuzzy_matching_config = {
            "enabled": self.config_manager.get_setting("bot_settings.fuzzy_matching_enabled", default=False),
            "multi_step_char_threshold": self.config_manager.get_setting("bot_settings.multi_step_char_threshold", default=20),
            "fuzzy_match_threshold": self.config_manager.get_setting("bot_settings.fuzzy_match_threshold", default=0.6)
        }

        trigger_config = self.config_manager.get_setting("bot_settings.recipe_trigger")
        self.trigger_x = trigger_config.get("check_pixel_x")
        self.trigger_y = trigger_config.get("check_pixel_y")
        self.expected_color = tuple(trigger_config.get("expected_color_rgb"))
        self.tolerance = trigger_config.get("tolerance", 10)

    def run(self):
        """Main bot loop. Waits for a recipe and processes it."""
        self.log.info(f"Waiting for a new recipe...")
        self._wait_for_recipe_trigger()

        self.log.debug(f"Recipe trigger detected. Reading recipe...")
        self._process_recipe()

    def _wait_for_recipe_trigger(self):
        """Waits for the pixel color that indicates a new recipe is available."""
        while not pyautogui.pixelMatchesColor(self.trigger_x, self.trigger_y, self.expected_color, tolerance=self.tolerance):
            pyautogui.sleep(self.loop_delay)

    def _is_page_active(self, page_number: int) -> bool:
        """Checks if an ingredient page indicator is active based on color saturation."""
        if not self.page_indicators or len(self.page_indicators) < page_number - 1:
            self.log.error(f"Page indicator for page {page_number} not found in config.")
            return False

        # page_number is 2 or 3, list is 0-indexed
        indicator = self.page_indicators[page_number - 2]
        x, y = indicator['x'], indicator['y']
        
        # Capture a small 1x1 region at the indicator's coordinates
        pixel_roi = {'left': x, 'top': y, 'width': 1, 'height': 1}
        pixel_img_bgra = capture_region(pixel_roi)

        if pixel_img_bgra is None:
            self.log.warning(f"Failed to capture pixel for page {page_number} indicator.")
            return False

        # Convert BGRA to BGR then to HSV
        pixel_bgr = cv2.cvtColor(pixel_img_bgra, cv2.COLOR_BGRA2BGR)
        pixel_hsv = cv2.cvtColor(pixel_bgr, cv2.COLOR_BGR2HSV)
        
        # Check the saturation value (index 1)
        saturation = pixel_hsv[0, 0][1]
        is_active = saturation >= 10
        self.log.debug(f"Page {page_number} indicator saturation: {saturation}. Active: {is_active}")
        return is_active

    def _process_page(self, required_steps: list):
        """Processes a single page of ingredients."""
        if not required_steps:
            return False

        self.log.info(f"Processing steps for current page: {required_steps}")
        available_on_page = self.ocr.process_ingredient_panel_roi(self.panel_roi, self.ingredient_slots)
        self.log.info(f"Available on page: {available_on_page}")
        if not available_on_page:
            return False

        if 'Sanitize' in available_on_page:
            self.log.info("Special Case: Chores")

            if "Mash" in available_on_page:
                self.log.debug("Extra special case: Trash mashing")
                
                press_key([self.input_keys[0]])
                press_key([self.input_keys[1]] * 10)
                press_key(self.input_keys[2])
                return True


            keys_to_press = self.input_keys[:len(available_on_page)]
            press_key(keys_to_press)


            return True

        if available_on_page and "Pour" in available_on_page[0]:
            self.log.info("Special Case: Beer")
            hold_key(self.input_keys[0], 1.0)
            return True

        

        keys_to_press = fuzzy_map_ingredients_to_keys(required_steps, available_on_page, self.input_keys, self.fuzzy_matching_config)
        
        self.log.info(f"Keys to press for this page: {keys_to_press}")
        press_key(keys_to_press)

        return False

    def _consolidate_recipe_pages(self, recipe_data):
        """
        Determines the last active page, consolidates extra steps onto it, and truncates the recipe data.
        - Assumes any extra steps are on the last active page 
        """

        # Start by assuming the last required page is the highest possible one (page 3, index 2).
        final_page_candidate = 3

        has_extra_steps = recipe_data[3] != []

        # Iterate downwards from page 3 to page 2 to find the last *required* page.
        while final_page_candidate > 1:

            if has_extra_steps:
                # any extra steps are assumed to be on the last active page
                page_is_required = self._is_page_active(final_page_candidate)
            else:
                # if there aren't any extra steps, the last page we need is the last one with instructions
                page_is_required = recipe_data[final_page_candidate-1] != []

            if page_is_required:
                # Since we are iterating downwards, the first required page we find is the last one.
                break
            else:
                # This page isn't needed, so the last required page must be before it.
                final_page_candidate -= 1

        last_page_index = final_page_candidate - 1
        # put extra steps on last available page to prevent extra screen grab
        if recipe_data[3]:
            recipe_data[last_page_index].extend(recipe_data[3])
        recipe_data = recipe_data[:final_page_candidate]

        return recipe_data, last_page_index



    def _process_recipe(self):
        """Processes a recipe page by page."""
        recipe_data = self.ocr.process_recipe_list_roi(self.recipe_roi)
        
        # Check if OCR returned anything meaningful
        if not any(recipe_data):
            self.log.warning("Recipe card detected, but failed to read any recipe text. Skipping this attempt.")
            pyautogui.sleep(self.loop_delay)
            return
        
        self.log.debug(f"Raw Recipe Data: {recipe_data}")

        recipe_data, last_page_index = self._consolidate_recipe_pages(recipe_data)

        self.log.info(f"New recipe detected! Data: {recipe_data}")


        for i, page_steps in enumerate(recipe_data): 
            special_case = self._process_page(page_steps)
            if special_case:
                break

            if i < last_page_index:
                self.log.info(f"Turning page...")
                press_key(self.page_turn_key)
                pyautogui.sleep(self.page_delay)

        
        # Process extra steps after handling all normal pages
        # extra_steps = recipe_data[3]
        # if extra_steps and not special_case:
        #     self.log.info("Processing extra steps...")
        #     self._process_page(extra_steps)

        self._serve_order()

    def _serve_order(self):
        """Presses the confirm key to serve the order."""
        self.log.info("Recipe complete. Pressing confirm key.")
        press_key(self.confirm_key)
        pyautogui.sleep(self.loop_delay) # Add a small delay after serving

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