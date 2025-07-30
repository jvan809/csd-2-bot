import pyautogui
import logging

log = logging.getLogger('csd2_bot')

def press_key(key: str):
    """
    Presses a single key using pyautogui.
    Logs the action.
    """
    try:
        pyautogui.press(key)
        log.info(f"Pressed key: {key}")
    except Exception as e:
        log.error(f"Failed to press key '{key}': {e}")