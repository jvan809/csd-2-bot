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
        target_h = 50
        h, w = image.shape[:2]
        if h == 0: return image # Avoid division by zero
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

