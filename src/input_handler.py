import pydirectinput
import logging

log = logging.getLogger('csd2_bot')

def press_key(key: str):
    """
    Presses a single key using pydirectinput for better game compatibility.
    Logs the action.
    """
    try:
        # Convert all keys to lowercase to ensure compatibility.
        # Games often expect the base key press (e.g., 'a') rather than a shifted one ('A').
        pydirectinput.press(key.lower())
        log.debug(f"Pressed key: {key}")
    except Exception as e:
        log.error(f"Failed to press key '{key}': {e}")