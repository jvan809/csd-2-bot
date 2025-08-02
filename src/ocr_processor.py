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
        label_mask_path = self.config_manager.get_setting("bot_settings.ingredient_mask_path")
        self.label_mask = cv2.imread(label_mask_path, cv2.IMREAD_GRAYSCALE)

    

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


    def process_ingredient_panel_roi(self, ingredient_panel_roi: dict, relative_ingredient_slot_rois: list[dict], return_confidence: bool = False) -> Union[list[str], list[tuple[str, float]]]:
        """
        Captures and OCRs the ingredient panel, returning a list of available ingredients.
        This is a high-level function that orchestrates the full pipeline.

        Args:
            ingredient_panel_roi: The ROI for the entire ingredient panel.
            relative_ingredient_slot_rois: A list of ROIs for each ingredient slot,
                                           relative to the main panel's ROI.
            return_confidence: Whether to return confidence scores with the text.
        """
        panel_image = capture_region(ingredient_panel_roi)
        if panel_image is None:
            return []

        results = []
        end_of_panel = False
        for slot_roi in relative_ingredient_slot_rois:
            y, x, w, h = slot_roi['top'], slot_roi['left'], slot_roi['width'], slot_roi['height']
            item_image = panel_image[y:y+h, x:x+w]

            if item_image.size == 0:
                log.warning(f"Ingredient slot ROI is malformed or has size 0: {slot_roi}")
                results.append(("", 0.0) if return_confidence else "")
                continue

            # Heuristic to detect if an ingredient slot is empty. Empty slots are
            # assumed to be a solid grey, whereas full slots have black text on a white background
            # We check the top-left pixel's BGR values, ignoring alpha.
            top_left_pixel = item_image[0, 0]
            is_white = np.all(top_left_pixel[:3] == 255)
            is_black = np.all(top_left_pixel[:3] == 0)
            if not is_white and not is_black:
                log.debug("Skipping empty ingredient slot (detected as non-white/black).")
                end_of_panel = True
                results.append(("", 0.0) if return_confidence else "")
                continue
            elif end_of_panel:
                # Thought it was the end of the panel but we were wrong
                log.warning("Missed Panel")
                end_of_panel = False

            # Where the mask is white, use the pixel from item_image. Where black, use white.
            masked_image = np.where(self.label_mask[:, :, None] == 255, item_image, 255)

            normalized_img = ImagePreprocessor.normalize(masked_image)
            processed_image = ImagePreprocessor.binarize(normalized_img, invert_colors=False)
            
            shear_factor = self.config_manager.get_setting("bot_settings.right_panel_shear_factor", default=0.14)
            processed_image = ImagePreprocessor.correct_shear(processed_image, shear_factor)

            ocr_data = self.text_parser.extract_structured_data(processed_image, psm=7)
            min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
            parsed_phrase, confidence = self.text_parser.parse_as_single_phrase(ocr_data, min_confidence=min_conf, return_confidence=True)
            if parsed_phrase:
                results.append((parsed_phrase, confidence) if return_confidence else parsed_phrase)
            else:
                log.warning("Label detected but no text found with sufficient confidence.")
                results.append(("", 0.0) if return_confidence else "")

        log.debug(f"Processed ingredient panel. Found: {results}")
        return results
