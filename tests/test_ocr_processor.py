import pytest
import cv2
import re
from pathlib import Path

# Add the project root to the Python path to allow imports from src
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ocr_processor import *

# Define the path to the test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_test_cases():
    """
    Dynamically discovers test cases by scanning the fixtures directory for image files.
    It pairs `*.png` files with `*.txt` files of the same name and parses the
    filename for test parameters based on a defined convention.

    Filename Convention:
    - `_invert`: Sets `invert_colors=True`.
    - `_psmX`: Sets the Page Segmentation Mode (e.g., `_psm7`).
    - `_panel`: Indicates a panel requiring `find_ingredient_boxes`.
    - `_confX`: Sets the minimum confidence for parsing (e.g., `_conf40`).
    """
    test_cases = []
    if not FIXTURES_DIR.is_dir():
        pytest.fail(f"Fixtures directory not found at {FIXTURES_DIR}")

    for image_path in FIXTURES_DIR.glob("*.png"):
        text_path = image_path.with_suffix('.txt')
        if not text_path.exists():
            print(f"Warning: Skipping test for '{image_path.name}' because matching .txt file is missing.")
            continue

        with open(text_path, 'r') as f:
            expected_text = f.read().strip()

        # Parse filename for parameters
        stem = image_path.stem
        invert_colors = "_invert" in stem
        is_panel = "_panel" in stem

        psm_match = re.search(r'_psm(\d+)', stem)
        psm_mode = int(psm_match.group(1)) if psm_match else 7 # Default to PSM 7

        conf_match = re.search(r'_conf(\d+)', stem)
        min_confidence = int(conf_match.group(1)) if conf_match else 50 # Default to 50

        test_cases.append(pytest.param(
            image_path, invert_colors, is_panel, expected_text, psm_mode, min_confidence, id=stem
        ))

    return test_cases

def _get_phrases_from_panel(image: np.ndarray, psm_mode: int, min_confidence: int, invert_colors: bool) -> list[str]:
    """Helper function to process a panel image and return a list of parsed phrases."""
    all_parsed_phrases = []
    boxes_and_contours = find_ingredient_boxes(image)
    panel_images = crop_image_by_boxes(image, boxes_and_contours)
    
    for item_image in panel_images:
        normalized_img = normalize_image(item_image)
        processed_image = binarize_image(normalized_img, invert_colors=invert_colors)
        if processed_image is None or processed_image.size == 0:
            continue

        ocr_data = extract_text_from_image(processed_image, psm=psm_mode)
        parsed_phrase = parse_single_phrase(ocr_data, min_confidence=min_confidence)
        if parsed_phrase:
            all_parsed_phrases.append(parsed_phrase)
    return all_parsed_phrases

def _get_ingredients_from_list(image: np.ndarray, psm_mode: int, min_confidence: int, invert_colors: bool) -> list[str]:
    """Helper function to process a recipe list image and return a list of ingredients."""
    all_parsed_ingredients = []
    processed_image = binarize_image(image, invert_colors=invert_colors)
    if processed_image is not None and processed_image.size > 0:
        ocr_data = extract_text_from_image(processed_image, psm=psm_mode)
        parsed_list = parse_ingredient_list(ocr_data, min_confidence=min_confidence)
        all_parsed_ingredients.extend(parsed_list)
    return all_parsed_ingredients

@pytest.mark.parametrize(
    "image_path, invert_colors, is_panel, expected_text, psm_mode, min_confidence",
    load_test_cases()
)
def test_ocr_pipeline(image_path, invert_colors, is_panel, expected_text, psm_mode, min_confidence):
    """
    Tests the full OCR pipeline by coordinating between different processing strategies.
    """
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    assert image is not None, f"Failed to load image: {image_path}"

    if is_panel:
        # Strategy for panel images: crop into individual items, then parse each as a single phrase.
        all_parsed_ingredients = _get_phrases_from_panel(image, psm_mode, min_confidence, invert_colors)
    else:
        # Strategy for non-panel images: treat as a single block of text (e.g., a recipe list).
        all_parsed_ingredients = _get_ingredients_from_list(image, psm_mode, min_confidence, invert_colors)

    # Filter out any empty strings that might result from failed OCR on some boxes.
    actual_text = "\n".join([ing for ing in all_parsed_ingredients if ing]).strip()
    
    assert actual_text.upper() == expected_text.upper()
