import cv2
import pytesseract
import numpy as np
import logging
from pytesseract import Output
from typing import Union
from src.config_manager import ConfigManager
from src.screen_capture import capture_region

log = logging.getLogger('csd2_bot')


class OcrProcessor:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._configure_tesseract()

    def _configure_tesseract(self):
        """Sets the Tesseract command path from the config file."""
        try:
            tesseract_path = self.config_manager.get_setting("bot_settings.tesseract_path")
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            log.debug(f"Tesseract path set to: {pytesseract.pytesseract.tesseract_cmd}")
        except Exception as e:
            log.error(f"Could not set Tesseract path from config. Ensure it's in your system PATH. Error: {e}")

    def _normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalizes an image for OCR by resizing to a standard height and adding padding.
        This is typically used for images of varying sizes, like cropped panel items.

        Args:
            image: The input image as a NumPy array.

        Returns:
            The normalized image.
        """
        # 1. Resize the image to a fixed height to improve OCR accuracy.
        # Tesseract works best with text that is at least 30px high.
        target_h = 50
        h, w = image.shape[:2]
        scale_ratio = target_h / h
        target_w = int(w * scale_ratio)
        resized_image = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        # 2. Add a white border (padding) to prevent characters from touching the edge.
        padding = 10
        num_channels = resized_image.shape[2] if len(resized_image.shape) > 2 else 1
        border_color = [255] * num_channels if num_channels > 1 else 255
            
        padded_image = cv2.copyMakeBorder(resized_image, padding, padding, padding, padding, cv2.BORDER_CONSTANT, value=border_color)
        
        log.debug("Image normalized with resizing and padding.")
        return padded_image

    def _binarize_image(self, image: np.ndarray, invert_colors: bool = False) -> np.ndarray | None:
        """
        Converts an image to a binary (black and white) format for OCR using
        grayscale conversion and Otsu's thresholding.

        Args:
            image: The input image as a NumPy array.
            invert_colors: If True, inverts the threshold for light text on dark backgrounds.

        Returns:
            The processed black-and-white image, or None if the input was invalid.
        """
        if image is None:
            log.error("Cannot binarize a None image.")
            return None

        # 1. Convert to grayscale, handling different channel counts.
        if len(image.shape) == 3 and image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        elif len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 2:
            gray = image  # Already grayscale
        else:
            log.error(f"Unsupported image shape for binarization: {image.shape}")
            return None

        # 2. Apply a threshold using Otsu's method to automatically find the best value.
        threshold_type = cv2.THRESH_BINARY_INV if invert_colors else cv2.THRESH_BINARY
        _, processed_image = cv2.threshold(gray, 0, 255, threshold_type + cv2.THRESH_OTSU)

        log.debug(f"Image binarized for OCR. Inverted colors: {invert_colors}")
        return processed_image

    def _correct_shear(self, image: np.ndarray, shear_factor: float) -> np.ndarray:
        """
        Corrects for horizontal shear in an image, common with italic-style fonts.

        Args:
            image: The input image with sheared text.
            shear_factor: The amount of shear to apply. Positive values correct a
                        right-leaning slant, negative values correct a left-leaning slant.

        Returns:
            The de-sheared image.
        """
        if shear_factor == 0.0:
            return image

        (h, w) = image.shape[:2]
        
        M = np.array([[1, shear_factor, 0], [0, 1, 0]], dtype=np.float32)

        log.debug(f"correct_shear: Applying shear factor of {shear_factor:.2f}.")
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

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

    def _extract_text_from_image(self, image: np.ndarray, psm: int = 7) -> dict:
        """
        Extracts structured word data from a pre-processed image using Tesseract.

        Args:
            image: The pre-processed black-and-white image.
            psm: The Page Segmentation Mode to use. Defaults to 7 (line of text).

        Returns:
            A dictionary containing structured data about the recognized words.
        """
        if image is None:
            log.error("Cannot extract text from a None image.")
            return {}
        try:
            # Base Tesseract configuration
            custom_config = f'--oem 3 --psm {psm}'

            data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
            log.debug(f"Extracted structured text data with {len(data.get('text', []))} potential words.")
            return data
        except pytesseract.TesseractNotFoundError:
            log.error("Tesseract executable not found. Ensure it is installed and the path is configured correctly.")
            return {}
        except Exception as e:
            log.error(f"An error occurred during OCR: {e}")
            return {}

    def _parse_single_phrase(self, ocr_data: dict, min_confidence: int = 50, return_confidence: bool = False) -> Union[str, tuple[str, float]]:
        """
        Parses OCR data assuming it represents a single phrase (e.g., one ingredient name).
        It concatenates all words with sufficient confidence into a single string.

        Args:
            ocr_data: The structured data dictionary from Pytesseract.
            min_confidence: The minimum confidence score to include a word.
            return_confidence: If True, returns a tuple with the phrase and its average confidence.

        Returns:
            A single string representing the recognized phrase, or a tuple with the phrase and confidence.
        """
        if not ocr_data or not ocr_data.get('text'):
            return ("", 0.0) if return_confidence else ""

        words = []
        confidences = []
        for i in range(len(ocr_data['text'])):
            confidence = int(ocr_data['conf'][i])
            if confidence >= min_confidence:
                text = ocr_data['text'][i].strip()
                if text:
                    words.append(text)
                    confidences.append(confidence)

        result = " ".join(words)
        log.debug(f"Parsed single phrase with min confidence {min_confidence}: '{result}'")
        
        if return_confidence:
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return result, avg_confidence
        else:
            return result

    def _parse_ingredient_list(self, ocr_data: dict, min_confidence: int = 50, return_confidence: bool = False) -> Union[list[str], list[tuple[str, float]]]:
        """
        Parses structured OCR data from a recipe list, intelligently grouping words
        into distinct ingredients based on proximity.

        Args:
            ocr_data: The structured data dictionary from Pytesseract.
            min_confidence: The minimum confidence score to include a word.
            return_confidence: If True, returns a list of tuples with phrase and average confidence.

        Returns:
            A list of strings or a list of (string, float) tuples.
        """
        if not ocr_data or not ocr_data.get('text'):
            return []

        horizontal_gap_threshold = self.config_manager.get_setting("bot_settings.panel_detection.horizontal_gap_threshold", default=30)

        # 1. Collect all valid words with their properties into a list of dicts
        words = []
        for i in range(len(ocr_data['text'])):
            confidence = int(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            if confidence >= min_confidence and text:
                words.append({
                    'text': text,
                    'left': int(ocr_data['left'][i]),
                    'width': int(ocr_data['width'][i]),
                    'line_num': int(ocr_data['line_num'][i]),
                    'block_num': int(ocr_data['block_num'][i]),
                    'conf': confidence
                })

        if not words:
            return []

        # 2. Sort words by reading order (block, line, then horizontal position)
        words.sort(key=lambda w: (w['block_num'], w['line_num'], w['left']))

        # 3. Group words into ingredients based on proximity
        results = []
        current_ingredient_words = [words[0]['text']]
        current_ingredient_confs = [words[0]['conf']]
        for i in range(1, len(words)):
            prev_word, current_word = words[i-1], words[i]
            same_line = current_word['block_num'] == prev_word['block_num'] and current_word['line_num'] == prev_word['line_num']

            if same_line and (current_word['left'] - (prev_word['left'] + prev_word['width'])) < horizontal_gap_threshold:
                current_ingredient_words.append(current_word['text'])
                current_ingredient_confs.append(current_word['conf'])
            else:
                phrase = " ".join(current_ingredient_words)
                if return_confidence:
                    avg_conf = sum(current_ingredient_confs) / len(current_ingredient_confs) if current_ingredient_confs else 0.0
                    results.append((phrase, avg_conf))
                else:
                    results.append(phrase)
                
                current_ingredient_words = [current_word['text']]
                current_ingredient_confs = [current_word['conf']]

        if current_ingredient_words:
            phrase = " ".join(current_ingredient_words)
            if return_confidence:
                avg_conf = sum(current_ingredient_confs) / len(current_ingredient_confs) if current_ingredient_confs else 0.0
                results.append((phrase, avg_conf))
            else:
                results.append(phrase)

        log.debug(f"Parsed ingredient list with min confidence {min_confidence}: {results}")
        return results


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
        if scale_factor > 1.0:
            log.debug(f"Upscaling recipe list image by factor of {scale_factor}")
            width = int(image_cv.shape[1] * scale_factor)
            height = int(image_cv.shape[0] * scale_factor)
            image_cv = cv2.resize(image_cv, (width, height), interpolation=cv2.INTER_CUBIC)

        # Recipe list has light text on a dark background, so inversion is needed.
        processed_image = self._binarize_image(image_cv, invert_colors=True)
        if processed_image is None or processed_image.size == 0:
            return []

        # Use PSM 6 for a single uniform block of text.
        ocr_data = self._extract_text_from_image(processed_image, psm=6)
        min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
        return self._parse_ingredient_list(ocr_data, min_confidence=min_conf)


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
            
            normalized_img = self._normalize_image(item_image)
            # The crop_image_by_boxes function places text on a white background.
            # Therefore, no color inversion is needed.
            processed_image = self._binarize_image(normalized_img, invert_colors=False)
            
            processed_image = self._correct_shear(processed_image, 0.14)

            if processed_image is None or processed_image.size == 0:
                continue

            ocr_data = self._extract_text_from_image(processed_image, psm=7)
            min_conf = self.config_manager.get_setting("bot_settings.min_confidence", default=50)
            parsed_phrase, confidence = self._parse_single_phrase(ocr_data, min_confidence=min_conf, return_confidence=True)
            if parsed_phrase:
                results.append((parsed_phrase, confidence) if return_confidence else parsed_phrase)

        log.debug(f"Processed ingredient panel. Found: {results}")
        return results
