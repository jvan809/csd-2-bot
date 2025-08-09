import cv2
import numpy as np
import logging

log = logging.getLogger('csd2_bot')

class ImagePreprocessor:
    """A collection of static methods for common image pre-processing tasks for OCR."""

    @staticmethod
    def normalize(image: np.ndarray) -> np.ndarray:
        """
        Normalizes an image for OCR by resizing to a standard height and adding padding.
        """
        target_h = 60
        h, w = image.shape[:2]
        if target_h < h:
            log.warning("Attempting to downsize image?")
        scale_ratio = target_h / h
        target_w = int(w * scale_ratio)
        resized_image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        padding = 10
        num_channels = resized_image.shape[2] if len(resized_image.shape) > 2 else 1
        border_color = [255] * num_channels if num_channels > 1 else 255
        padded_image = cv2.copyMakeBorder(resized_image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=border_color)
        
        log.debug("Image normalized with resizing and padding.")
        return padded_image

    @staticmethod
    def binarize(image: np.ndarray, invert_colors: bool = False) -> np.ndarray | None:
        """
        Converts an image to a binary (black and white) format using Otsu's thresholding.
        """
        if image is None:
            log.error("Cannot binarize a None image.")
            return None

        if len(image.shape) == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        elif len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 2:
            gray = image
        else:
            log.error(f"Unsupported image shape for binarization: {image.shape}")
            return None

        threshold_type = cv2.THRESH_BINARY_INV if invert_colors else cv2.THRESH_BINARY
        _, processed_image = cv2.threshold(gray, 0, 255, threshold_type + cv2.THRESH_OTSU)
        log.debug(f"Image binarized for OCR. Inverted colors: {invert_colors}")
        return processed_image

    @staticmethod
    def correct_shear(image: np.ndarray, shear_factor: float) -> np.ndarray:
        """Corrects for horizontal shear in an image (e.g., italics)."""
        if shear_factor == 0.0:
            return image
        (h, w) = image.shape[:2]
        M = np.array([[1, shear_factor, 0], [0, 1, 0]], dtype=np.float32)
        log.debug(f"Applying shear factor of {shear_factor:.2f}.")
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    @staticmethod
    def upscale(image: np.ndarray, scale_factor: float) -> np.ndarray:
        """Upscales an image by a given factor."""
        if scale_factor <= 1.0:
            if scale_factor < 1.0:
                log.warning(f"Downscaling (factor {scale_factor}) is not supported by the upscale function. Returning unaltered image")
            return image
        log.debug(f"Upscaling image by factor of {scale_factor}")
        width = int(image.shape[1] * scale_factor)
        height = int(image.shape[0] * scale_factor)
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)

    @staticmethod
    def mask_by_coloured_text(hsv_image: np.ndarray, saturation_threshold: int, value_threshold: int) -> np.ndarray:
        """
        Creates a binary mask from an HSV image to isolate bright, colored text.

        Pixels with saturation > saturation_threshold AND value > value_threshold
        will be white, others will be black. This is effective for isolating
        colored text from grey backgrounds and dark shadows.

        Args:
            hsv_image: The input image in HSV format.
            saturation_threshold: The saturation threshold (0-255).
            value_threshold: The value (brightness) threshold (0-255).

        Returns:
            A combined binary mask (np.ndarray).
        """
        if hsv_image is None or len(hsv_image.shape) != 3 or hsv_image.shape[2] != 3:
            log.error("Invalid HSV image provided for colored text mask creation.")
            # Return an empty mask of the correct type to avoid downstream errors
            return np.zeros((0, 0), dtype=np.uint8)

        # Create a mask for pixels with sufficient saturation (color)
        saturation_channel = hsv_image[:, :, 1]
        _, saturation_mask = cv2.threshold(saturation_channel, saturation_threshold, 255, cv2.THRESH_BINARY)

        # Create a mask for pixels with sufficient value (brightness) to remove shadows
        value_channel = hsv_image[:, :, 2]
        _, value_mask = cv2.threshold(value_channel, value_threshold, 255, cv2.THRESH_BINARY)

        # Combine the masks: a pixel must be both saturated AND bright
        combined_mask = cv2.bitwise_and(saturation_mask, value_mask)

        log.debug(f"Created colored text mask with sat_thresh={saturation_threshold}, val_thresh={value_threshold}.")

        return combined_mask
