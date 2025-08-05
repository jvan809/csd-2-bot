import cv2
import numpy as np
import logging
from typing import Union
from src.config_manager import ConfigManager
from src.screen_capture import capture_region
from src.image_preprocessor import ImagePreprocessor
from src.text_parser import TextParser

log = logging.getLogger('csd2_bot')


class OcrProcessor:
    """Orchestrates screen capture, image processing, and text recognition for the game."""
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.text_parser = TextParser(config_manager)

    def _find_ingredient_boxes(self, panel_image: np.ndarray) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
        """
        Finds the coordinates of individual ingredient text boxes within a larger panel image.
        This is used for panels with multiple distinct items (the available ingredients list).

        Args:
            panel_image: The image of the entire ingredients panel.

        Returns:
            A list of tuples, where each tuple contains the bounding box (x, y, w, h)
            and the corresponding contour, sorted in column-first reading order.
        """
        if panel_image is None:
            log.error("Cannot find boxes in a None image.")
            return []

        threshold_val = self.config_manager.get_setting("bot_settings.panel_detection.threshold_value", default=245)
        min_area = self.config_manager.get_setting("bot_settings.panel_detection.min_area", default=1000)
        min_aspect_ratio = self.config_manager.get_setting("bot_settings.panel_detection.min_aspect_ratio", default=2.0)

        # 1. Pre-process the image to find the white background of the text boxes.
        gray = cv2.cvtColor(panel_image, cv2.COLOR_BGRA2GRAY)
        _, thresh = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)

        # 2. Find contours of the white boxes.
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes_and_contours = []
        for contour in contours:
            # 3. Get the bounding box and filter based on size/shape to find plausible text boxes.
            rect = cv2.boundingRect(contour)
            x, y, w, h = rect
            area = w * h
            aspect_ratio = w / float(h) if h > 0 else 0

            # These filter values are heuristics designed to find boxes that are wider than they are tall.
            if min_area < area and min_aspect_ratio < aspect_ratio:
                boxes_and_contours.append((rect, contour))

        # 4. Sort boxes in column reading order (left top-to-bottom, then right top-to-bottom).
        # This is crucial for mapping to the correct keyboard keys
        boxes_and_contours.sort(key=lambda b: (b[0][0], b[0][1]))

        log.debug(f"Programmatically found {len(boxes_and_contours)} ingredient boxes.")
        return boxes_and_contours

    def _crop_image_by_boxes(self, image: np.ndarray, boxes_and_contours: list[tuple[tuple[int, int, int, int], np.ndarray]]) -> list[np.ndarray]:
        """
        Crops a larger panel into sub-images of UI elements using bounding boxes and
        applies a mask derived from the corresponding contour to isolate the element.
        """
        cropped_images = []
        for rect, contour in boxes_and_contours:
            x, y, w, h = rect
            # 1. Crop the original image to the bounding rectangle of the contour.
            cropped_img = image[y:y+h, x:x+w].copy()

            # 2. Create a mask from the CONVEX HULL of the contour.
            # The convex hull creates a solid shape around the element, ignoring holes
            # caused by text, which prevents letters from being clipped.
            hull = cv2.convexHull(contour)
            mask = np.zeros(cropped_img.shape[:2], dtype=np.uint8)
            shifted_hull = hull - (x, y) # Adjust hull to the cropped image's coordinate system.
            cv2.drawContours(mask, [shifted_hull], -1, (255), -1) # Fill the hull shape with white.

            # 3. Composite the image to place the UI element on a pure white background.
            # This robustly removes the rounded corner artifacts without needing extra flood-fills.
            foreground = cv2.bitwise_and(cropped_img, cropped_img, mask=mask)
            background = cv2.bitwise_and(np.full(cropped_img.shape, 255, dtype=cropped_img.dtype), np.full(cropped_img.shape, 255, dtype=cropped_img.dtype), mask=cv2.bitwise_not(mask))
            masked_image = cv2.add(foreground, background)
            cropped_images.append(masked_image)
        return cropped_images

    def process_recipe_list_roi(self, roi: dict, return_confidence: bool = False) -> Union[list[str], list[tuple[str, float]]]:
        """
        Captures and OCRs the recipe list region, returning a list of required steps.
        This is a high-level function that orchestrates the full pipeline.
        """
        image_cv = capture_region(roi)  # Returns a BGRA numpy array
        if image_cv is None:
            return []

        # Upscale the image to improve OCR on potentially small text
        scale_factor = self.config_manager.get_setting("bot_settings.ocr_upscale_factor", default=1.0)
        upscaled_image = ImagePreprocessor.upscale(image_cv, scale_factor)

        # Recipe list has light text on a dark background, so inversion is needed.
        processed_image = ImagePreprocessor.binarize(upscaled_image, invert_colors=True)
        if processed_image is None or processed_image.size == 0:
            return []

        # Use PSM 6 for a single uniform block of text.
        ocr_data = self.text_parser.extract_structured_data(processed_image, psm=6)
        min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
        return self.text_parser.parse_as_ingredient_list(ocr_data, min_confidence=min_conf, return_confidence=return_confidence)


    def process_ingredient_panel_roi(self, roi: dict, return_confidence: bool = False) -> Union[list[str], list[tuple[str, float]]]:
        """
        Captures and OCRs the ingredient panel, returning a list of available ingredients.
        This is a high-level function that orchestrates the full pipeline.
        """
        image_cv = capture_region(roi)  # Returns a BGRA numpy array
        if image_cv is None:
            return []

        results = []
        boxes_and_contours = self._find_ingredient_boxes(image_cv)
        if not boxes_and_contours:
            return []

        panel_images = self._crop_image_by_boxes(image_cv, boxes_and_contours)

        for item_image in panel_images:
            
            normalized_img = ImagePreprocessor.normalize(item_image)
            # The crop_image_by_boxes function places text on a white background.
            # Therefore, no color inversion is needed.
            processed_image = ImagePreprocessor.binarize(normalized_img, invert_colors=False)
            
            shear_factor = self.config_manager.get_setting("bot_settings.right_panel_shear_factor", default=0.14)
            processed_image = ImagePreprocessor.correct_shear(processed_image, shear_factor)

            if processed_image is None or processed_image.size == 0:
                continue

            ocr_data = self.text_parser.extract_structured_data(processed_image, psm=7)
            min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
            parsed_phrase, confidence = self.text_parser.parse_as_single_phrase(ocr_data, min_confidence=min_conf, return_confidence=True)
            if parsed_phrase:
                results.append((parsed_phrase, confidence) if return_confidence else parsed_phrase)

        log.debug(f"Processed ingredient panel. Found: {results}")
        return results
