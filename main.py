import pyautogui
from src.logger_setup import setup_logger
from src.config_manager import ConfigManager
from src.input_handler import press_key
from src.ocr_processor import configure_tesseract, process_recipe_list_roi, process_ingredient_panel_roi
from src.bot_logic import map_ingredients_to_keys
import logging

def run_game_loop(config_manager: ConfigManager):
    """

    Runs one full cycle of the gameplay loop:
    1. Waits for a new recipe.
    2. Processes all pages of ingredients for that recipe.
    3. Serves the order.
    """
    log = logging.getLogger('csd2_bot')

    # --- 1. Load Config ---
    recipe_roi = config_manager.get_setting("ocr_regions.recipe_list_roi")
    panel_roi = config_manager.get_setting("ocr_regions.ingredient_panel_roi")
    input_keys = config_manager.get_setting("controls.input_keys")
    page_turn_key = config_manager.get_setting("controls.page_turn_key")
    confirm_key = config_manager.get_setting("controls.confirm_key")
    loop_delay = config_manager.get_setting("bot_settings.main_loop_delay", default=1.0)
    key_delay = config_manager.get_setting("bot_settings.key_delay", default=0.05)
    page_delay = config_manager.get_setting("bot_settings.page_delay", default=0.25)
    
          
    # --- 2. Wait for Recipe ---
    log.info("Waiting for a new recipe...")
    remaining_steps = []
    while not remaining_steps:
        remaining_steps = process_recipe_list_roi(recipe_roi)
        if not remaining_steps:
            pyautogui.sleep(loop_delay) # Wait before trying again

    log.info(f"New recipe detected! Steps: {remaining_steps}")

    # --- 3. Ingredient Page Loop ---
    page_turns = 0
    max_page_turns = 2 # Initial page + 2 turns

    while remaining_steps and page_turns <= max_page_turns:
        log.debug(f"Processing page {page_turns + 1}. Remaining steps: {remaining_steps}")

        # a. Get available ingredients
        available_on_page = process_ingredient_panel_roi(panel_roi)
        log.info(f"Available on page: {available_on_page}")

        # b. Map steps to keys
        keys_to_press, matched_ingredients = map_ingredients_to_keys(remaining_steps, available_on_page, input_keys)
        log.info(f"Matched ingredients: {matched_ingredients}. Keys to press: {keys_to_press}")

        # c. Execute key presses and update state
        if keys_to_press:
            for key in keys_to_press:
                press_key(key)
                pyautogui.sleep(key_delay) # Small delay between key presses

            # Remove matched ingredients from the remaining steps, handling duplicates correctly
            temp_matched = list(matched_ingredients)
            new_remaining_steps = []
            for step in remaining_steps:
                if step in temp_matched:
                    temp_matched.remove(step) # Remove one instance of the matched step
                else:
                    new_remaining_steps.append(step)
            remaining_steps = new_remaining_steps

        # d. Turn page if necessary
        if remaining_steps and page_turns < max_page_turns:
            log.debug("There are remaining steps, turning page.")
            press_key(page_turn_key)
            page_turns += 1
            pyautogui.sleep(page_delay) # Wait for page turn animation
        else:
            break # No more steps or max pages reached

    # --- 4. Serve Order ---
    if not remaining_steps:
        log.info("Recipe complete. Pressing confirm key.")
        press_key(confirm_key)
    else:
        log.warning(f"Finished recipe attempt with remaining steps: {remaining_steps}. Manual intervention may be needed.")

def main():      
    """Main application entry point."""
    # 1. Create config manager first, as it's needed by the logger
    config_manager = ConfigManager()

    # 2. Setup logger using the config
    log = setup_logger(config_manager)

    # 3. Configure Tesseract now that the logger is ready
    configure_tesseract()

    log.info("Starting CSD2 Bot...")
    
    # Enable PyAutoGUI failsafe
    if config_manager.get_setting("bot_settings.enable_failsafe", default=True):
        pyautogui.FAILSAFE = True
        log.info("PyAutoGUI failsafe enabled. Move mouse to top-left corner to stop.")
    else:
        pyautogui.FAILSAFE = False
        log.warning("PyAutoGUI failsafe is disabled.")

    try:
        # Main bot loop
        log.info("Bot is running. Press Ctrl+C in the console to exit.")
        while True:
            run_game_loop(config_manager)
            delay = config_manager.get_setting("bot_settings.main_loop_delay", default=1.0)
            log.info(f"Loop finished. Waiting {delay}s before checking for a new recipe.")
            pyautogui.sleep(delay)

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