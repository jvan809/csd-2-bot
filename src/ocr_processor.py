import cv2
import numpy as np
import logging
from typing import Union, List
from pathlib import Path
from datetime import datetime
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
        
        # --- Page Color Definitions ---
        # Using hardcoded values as requested. These could be moved to config.json later.
        self.PAGE_HUE_RANGES = {
            1: (125, 135), # Purple
            2: (0, 5),     # Red (lower range)
            3: (15, 25),   # Yellow
        }
        # Red's hue is circular (0-179), so it needs a check at the top of the range too.
        self.PAGE_HUE_RANGES_RED_UPPER = (175, 179)
        self.EMPTY_SLOT_SATURATION_THRESHOLD = 50

    def _is_slot_empty(self, hsv_image: np.ndarray, roi: dict) -> bool:
        """Checks if a recipe slot is empty by checking the saturation of the middle pixel."""
        x, y, w, h = roi['left'], roi['top'], roi['width'], roi['height']
        middle_x, middle_y = x + w // 2, y + h // 2
        
        if not (0 <= middle_y < hsv_image.shape[0] and 0 <= middle_x < hsv_image.shape[1]):
            log.warning(f"Middle pixel ({middle_x}, {middle_y}) for ROI {roi} is out of bounds for image shape {hsv_image.shape}.")
            return True # Treat out-of-bounds as empty

        saturation = hsv_image[middle_y, middle_x][1]
        return saturation < self.EMPTY_SLOT_SATURATION_THRESHOLD

    def _get_page_from_hue(self, hsv_image: np.ndarray, roi: dict) -> int:
        """Determines the page number (1, 2, or 3) from the hue of the middle pixel."""
        x, y, w, h = roi['left'], roi['top'], roi['width'], roi['height']
        middle_x, middle_y = x + w // 2, y + h // 2

        if not (0 <= middle_y < hsv_image.shape[0] and 0 <= middle_x < hsv_image.shape[1]):
            return 0 # Unknown page

        hue = hsv_image[middle_y, middle_x][0]

        for page, (lower, upper) in self.PAGE_HUE_RANGES.items():
            if lower <= hue <= upper:
                return page
        
        lower_red, upper_red = self.PAGE_HUE_RANGES_RED_UPPER
        if lower_red <= hue <= upper_red:
            log.info("Red Upper range used for page determiniation")
            return 2 # Page 2 (Red)

        return 0 # Unknown page

    def _ocr_single_slot(self, image_slice: np.ndarray) -> str:
        """Performs the full OCR pipeline on a single recipe slot image."""
        processed_image = ImagePreprocessor.binarize(image_slice, invert_colors=True)
        processed_image = ImagePreprocessor.normalize(processed_image)
        
        if processed_image is None or processed_image.size == 0:
            log.warning("Empty image passed to processor")
            return ""


        ocr_data = self.text_parser.extract_structured_data(processed_image, psm=7) # PSM 7 for single line
        min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
        
        parsed_text, confidence = self.text_parser.parse_as_single_phrase(ocr_data, min_confidence=min_conf, return_confidence=True)
        log.debug(f"{parsed_text}, {confidence}")

        if not parsed_text:
            self._save_failed_ocr_image(image_slice)
            self._save_failed_ocr_image(processed_image)
            debug_text, confidence = self.text_parser.parse_as_single_phrase(ocr_data, min_confidence=0, return_confidence=True)
            log.warning(f"OCR failed. Best guess {debug_text} with confidence {confidence}")

        return parsed_text

    def _save_failed_ocr_image(self, image: np.ndarray):
        """Saves an image that failed OCR to a debug directory."""
        fails_dir = Path("debug/ocr_fails")
        fails_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = fails_dir / f"failed_recipe_slot_{timestamp}.png"
        try:
            cv2.imwrite(str(filename), image)
            log.info(f"Saved failing OCR image to: {filename}")
        except Exception as e:
            log.error(f"Could not save failing OCR image to {filename}. Error: {e}")



    def process_recipe_list_roi(self, roi: dict) -> List[List[str]]:
        """
        Captures and OCRs the recipe list region, sorting steps by page color.

        Returns:
            A list of lists of strings, structured as [page1_steps, page2_steps, page3_steps, extra_steps].
        """
        recipe_pages = [[], [], []]
        extra_steps = []
        final_structure = [recipe_pages[0], recipe_pages[1], recipe_pages[2], extra_steps]

        panel_image_bgra = capture_region(roi)
        if panel_image_bgra is None:
            log.warning("Failed to capture recipe panel image.")
            return final_structure

        panel_image_bgr = cv2.cvtColor(panel_image_bgra, cv2.COLOR_BGRA2BGR)
        panel_image_hsv = cv2.cvtColor(panel_image_bgr, cv2.COLOR_BGR2HSV)

        recipe_indicator_rois = self.config_manager.get_setting("recipe_layout.recipe_indicator_rois")
        recipe_slot_rois = self.config_manager.get_setting("recipe_layout.recipe_slot_rois")

        if not recipe_indicator_rois:
            log.error("`recipe_indicator_rois` not found in config. Run setup.py.")
            return final_structure

        num_steps_found = 0
        for indicator_roi, slot_roi in zip(recipe_indicator_rois, recipe_slot_rois):
            if self._is_slot_empty(panel_image_hsv, indicator_roi):
                log.debug(f"{num_steps_found} steps found in recipe panel")
                break

            num_steps_found += 1
            page_num = self._get_page_from_hue(panel_image_hsv, indicator_roi)

            if page_num == 0:
                log.warning(f"Could not determine page number for recipe slot at {indicator_roi}. Skipping.")
                continue

            x, y, w, h = slot_roi['left'], slot_roi['top'], slot_roi['width'], slot_roi['height']
            slot_image = panel_image_bgr[y:y+h, x:x+w]

            ocr_text = self._ocr_single_slot(slot_image)

            if ocr_text:
                recipe_pages[page_num - 1].append(ocr_text)


        vertical_coords = self.config_manager.get_setting("recipe_layout.vertical_coords")
        if not vertical_coords:
            log.error("`vertical_coords` not found in config. Run setup.py.")
            return final_structure

        if num_steps_found == 0:
            extra_top = vertical_coords.get('panel_top', 0)
        elif num_steps_found < 6:
            extra_top = vertical_coords.get('line_one_bottom', 0)
        else:
            extra_top = vertical_coords.get('line_two_bottom')

        
        extra_bottom = vertical_coords.get('panel_bottom', 0)
        
        if extra_top >= extra_bottom:
            log.error("Setup determination of recipe panel Failed. Please Rerun setup.py")
            return final_structure

        extra_image = panel_image_hsv[extra_top:extra_bottom, :]
        extra_image = ImagePreprocessor.mask_by_coloured_text(extra_image, 38, 200)

        scale_factor = self.config_manager.get_setting("bot_settings.ocr_upscale_factor", default=1.0)
        upscaled_image = ImagePreprocessor.upscale(extra_image, scale_factor)
        processed_image = ImagePreprocessor.binarize(upscaled_image, invert_colors=True)
        
        if processed_image is not None and processed_image.size > 0:
            ocr_data = self.text_parser.extract_structured_data(processed_image, psm=6)
            min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
            parsed_list = self.text_parser.parse_as_ingredient_list(ocr_data, min_confidence=min_conf)
            if parsed_list:
                extra_steps.append(" ".join(parsed_list))

        log.debug(f"Processed recipe panel. Page 1: {final_structure[0]}, Page 2: {final_structure[1]}, Page 3: {final_structure[2]}, Extra: {final_structure[3]}")
        return final_structure


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
        null_result = ("", 0.0) if return_confidence else ""
        panel_image = capture_region(ingredient_panel_roi)
        if panel_image is None:
            return []

        results = []
        end_of_panel = 0
        for i, slot_roi in enumerate(relative_ingredient_slot_rois):
            y, x, w, h = slot_roi['top'], slot_roi['left'], slot_roi['width'], slot_roi['height']
            item_image = panel_image[y:y+h, x:x+w]

            if item_image.size == 0:
                log.warning(f"Ingredient slot ROI is malformed or has size 0: {slot_roi}")
                results.append(null_result)
                continue

            # Heuristic to detect if an ingredient slot is empty. Empty slots are
            # assumed to be a solid grey, whereas full slots have black text on a white background
            # We check the top-left pixel's BGR values, ignoring alpha.
            top_left_pixel = item_image[0, 0]
            is_white = np.all(top_left_pixel[:3] == 255)
            is_black = np.all(top_left_pixel[:3] == 0)
            if not is_white and not is_black:
                log.debug("Skipping empty ingredient slot (detected as non-white/black).")
                end_of_panel = i
                
                continue
            elif end_of_panel:
                # Thought it was the end of the panel but we were wrong
                log.warning("Missed Panel")
                results.extend([null_result]*(i-end_of_panel))
                end_of_panel = 0

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
                self._save_failed_ocr_image(processed_image)
                debug_phrase, confidence = self.text_parser.parse_as_single_phrase(ocr_data, min_confidence=0, return_confidence=True)
                log.warning(f"Best Guess: {debug_phrase} with confidence {confidence}")
                results.append(null_result)

        log.debug(f"Processed ingredient panel. Found: {results}")
        return results
