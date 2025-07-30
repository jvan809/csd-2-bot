import pyautogui
from src.logger_setup import setup_logger
from src.config_manager import ConfigManager

def main():
    """Main application entry point."""
    log = setup_logger()
    log.info("Starting CSD2 Bot...")

    config_manager = ConfigManager()
    
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
            # TODO: Implement core bot logic here in Phase 4
            # 1. Capture screen regions
            # 2. Process with OCR
            # 3. Get key presses from bot_logic
            # 4. Execute key presses
            
            print(".", end="", flush=True) # Placeholder for activity
            pyautogui.sleep(2) # Use pyautogui.sleep() to allow the failsafe to trigger

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