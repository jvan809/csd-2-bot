import pydirectinput
import logging
import time

log = logging.getLogger('csd2_bot')

def press_key(keys: str):
    """
    Presses a key or list of keys using pydirectinput
    converts all keys to lower case
    Logs the action.
    """
    if len(keys) == 0:
        log.debug("No keys to press")
        return

    if type(keys) == str:
        keys = [keys]

    keys = [key.lower() for key in keys]


    try:
        # Convert all keys to lowercase to ensure compatibility.
        # Games often expect the base key press (e.g., 'a') rather than a shifted one ('A').
        success = pydirectinput.press(keys)
        # Log the actual key being sent to the input handler
        if success:
            log.debug(f"Pressed key: {keys}")
        else:
            log.warning(f"Failed to press key {keys}")

    except Exception as e:
        log.error(f"Failed to press key '{keys}': {e}")


def hold_key(key, seconds):
    """
    Holds a key for a specified period of time.
    """
    key = key.lower()

    down_success = pydirectinput.keyDown(key)
    time.sleep(seconds)
    up_success = pydirectinput.keyUp(key)

    if down_success and up_success:
        log.debug(f"Held Key {key} for {seconds} s")
    else:
        log.warning(f"Failed to hold key {key}")
