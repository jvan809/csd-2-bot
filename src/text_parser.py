import pytesseract
from pytesseract import Output
import logging
from typing import Union
from src.config_manager import ConfigManager

log = logging.getLogger('csd2_bot')

class TextParser:
    """Handles Tesseract configuration, execution, and parsing of OCR data."""

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

    def extract_structured_data(self, image, psm: int = 7) -> dict:
        """Extracts structured word data from a pre-processed image using Tesseract."""
        if image is None:
            log.error("Cannot extract text from a None image.")
            return {}
        try:
            
            custom_config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist= 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
            log.debug(f"Extracted structured text data with {len(data.get('text', []))} potential words.")
            return data
        except pytesseract.TesseractNotFoundError:
            log.error("Tesseract executable not found. Ensure it is installed and the path is configured correctly.")
            return {}
        except Exception as e:
            log.error(f"An error occurred during OCR: {e}")
            return {}

    def _filter_words_by_confidence(self, ocr_data: dict, min_confidence: int) -> list[dict]:
        """Filters words from OCR data based on a minimum confidence score and returns structured data."""
        if not ocr_data or not ocr_data.get('text'):
            return []

        filtered_words = []
        for i in range(len(ocr_data['text'])):
            confidence = int(ocr_data['conf'][i])
            text = ocr_data['text'][i].strip()
            if text and confidence >= min_confidence:
                filtered_words.append({
                    'text': text,
                    'left': int(ocr_data['left'][i]),
                    'width': int(ocr_data['width'][i]),
                    'line_num': int(ocr_data['line_num'][i]),
                    'block_num': int(ocr_data['block_num'][i]),
                    'conf': confidence
                })
        return filtered_words

    def parse_as_single_phrase(self, ocr_data: dict, min_confidence: int, return_confidence: bool = False) -> Union[str, tuple[str, float]]:
        """Parses OCR data assuming it represents a single phrase (e.g., one ingredient name)."""
        filtered_words = self._filter_words_by_confidence(ocr_data, min_confidence)
        if not filtered_words:
            return ("", 0.0) if return_confidence else ""

        words = [word['text'] for word in filtered_words]
        confidences = [word['conf'] for word in filtered_words]

        result = " ".join(words)
        log.debug(f"Parsed single phrase with min confidence {min_confidence}: '{result}'")
        
        if return_confidence:
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            return result, avg_confidence
        else:
            return result

    def parse_as_ingredient_list(self, ocr_data: dict, min_confidence: int, return_confidence: bool = False) -> Union[list[str], list[tuple[str, float]]]:
        """Parses structured OCR data, intelligently grouping words into distinct ingredients."""
        words = self._filter_words_by_confidence(ocr_data, min_confidence)
        if not words: return []

        horizontal_gap_threshold = self.config_manager.get_setting("bot_settings.panel_detection.horizontal_gap_threshold", default=30)

        words.sort(key=lambda w: (w['block_num'], w['line_num'], w['left']))

        results, current_words, current_confs = [], [words[0]['text']], [words[0]['conf']]
        for i in range(1, len(words)):
            prev_word, current_word = words[i-1], words[i]
            same_line = current_word['block_num'] == prev_word['block_num'] and current_word['line_num'] == prev_word['line_num']

            if same_line and (current_word['left'] - (prev_word['left'] + prev_word['width'])) < horizontal_gap_threshold:
                current_words.append(current_word['text'])
                current_confs.append(current_word['conf'])
            else:
                self._add_phrase_to_results(results, current_words, current_confs, return_confidence)
                current_words, current_confs = [current_word['text']], [current_word['conf']]

        if current_words:
            self._add_phrase_to_results(results, current_words, current_confs, return_confidence)

        log.debug(f"Parsed ingredient list with min confidence {min_confidence}: {results}")
        return results

    def _add_phrase_to_results(self, results: list, words: list, confs: list, return_confidence: bool):
        """Helper to construct and append a phrase to the results list."""
        phrase = " ".join(words)
        if return_confidence:
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            results.append((phrase, avg_conf))
        else:
            results.append(phrase)
