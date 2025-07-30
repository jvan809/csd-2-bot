import mss
import numpy as np
import logging

log = logging.getLogger('csd2_bot')

def capture_region(roi: dict) -> np.ndarray | None:
    """
    Captures a specific region of the screen.
    The ROI should be a dictionary with 'top', 'left', 'width', 'height'.
    Returns the captured image as a NumPy array.
    """
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(roi)
            # Convert to a NumPy array
            img = np.array(sct_img) # BGRA format
            log.debug(f"Captured screen region at {roi}")
            return img
    except mss.exception.ScreenShotError as e:
        log.error(f"Failed to capture screen region at {roi}: {e}")
        return None