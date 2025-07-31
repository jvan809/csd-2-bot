import pytest
import cv2
import numpy as np
from pathlib import Path
import sys

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.screen_capture import capture_region
from src.ocr_processor import configure_tesseract
from src.ocr_processor import (
    find_ingredient_boxes,
    crop_image_by_boxes,
    normalize_image,
    binarize_image,
    extract_text_from_image,
    parse_single_phrase,
    parse_ingredient_list,
    correct_shear,
)

# Configure Tesseract before running any tests that use OCR
configure_tesseract()

# --- Test Configuration ---
# This is a manual integration test. It requires the game to be running and visible.
# It is skipped by default to prevent it from running in an automated test environment.
# To run this test:
# 1. Open the game and go to a level where the ingredient panel is visible.
# 2. Update the `MANUAL_INGREDIENT_PANEL_ROI` with the correct pixel coordinates for your screen.
#    You can use a screenshot tool (like Windows Snipping Tool or ShareX) to find these coordinates.
# 3. Comment out or remove the `@pytest.mark.skip` line below.
# 4. Run pytest from your terminal: `pytest tests/test_manual_integration.py -s` (the -s flag shows print output)

# --- Debugging Configuration ---
# Set to True to display the black-and-white images that are sent to OCR.
# A window will pop up for each image; press any key to continue.
SHOW_PREPROCESSED_IMAGES = True
PERFORM_SHEAR_CORRECTION = True
# This value will need to be tuned experimentally.
# Positive values correct a right-leaning slant.
# Negative values correct a left-leaning slant.
SHEAR_FACTOR = 0.14

MANUAL_INGREDIENT_PANEL_ROI = {
    "left": 1610,  # X coordinate of the top-left corner
    "top": 146,    # Y coordinate of the top-left corner
    "width": 305,  # Width of the region
    "height": 364, # Height of the region
}

# @pytest.mark.skip(reason="Manual test: requires game to be running and ROI to be configured.")
def test_live_ocr_on_ingredient_panel():
    """
    Captures the ingredient panel from a live game screen, processes it with OCR,
    and prints the results for manual verification.
    """
    print("\n--- Starting Live OCR Test ---")
    print(f"Capturing region: {MANUAL_INGREDIENT_PANEL_ROI}")

    # 1. Capture the screen region using the manual coordinates
    panel_image_pil = capture_region(MANUAL_INGREDIENT_PANEL_ROI)
    assert panel_image_pil is not None, "Screen capture failed. Is the region valid?"

    # Convert to OpenCV format
    panel_image_cv = cv2.cvtColor(np.array(panel_image_pil), cv2.COLOR_RGB2BGR)

    # 2. Process the captured image using the OCR pipeline
    all_parsed_phrases = []
    boxes_and_contours = find_ingredient_boxes(panel_image_cv)

    if not boxes_and_contours:
        pytest.fail("No ingredient boxes were found in the captured region. Check ROI or in-game screen.")

    print(f"Found {len(boxes_and_contours)} potential ingredient boxes.")
    panel_images = crop_image_by_boxes(panel_image_cv, boxes_and_contours)

    for i, item_image in enumerate(panel_images):
        image_to_process = item_image


        normalized_img = normalize_image(image_to_process)
        # For the ingredient panel, text is black on white, so no inversion is needed
        processed_image = binarize_image(normalized_img, invert_colors=False)


        if PERFORM_SHEAR_CORRECTION:
            processed_image = correct_shear(processed_image, SHEAR_FACTOR)


        if SHOW_PREPROCESSED_IMAGES and processed_image is not None:
            cv2.imshow(f"Processed Ingredient {i+1}", processed_image)
            cv2.waitKey(0)
            cv2.destroyWindow(f"Processed Ingredient {i+1}")

        if processed_image is None or processed_image.size == 0:
            continue

        ocr_data = extract_text_from_image(processed_image, psm=7)
        # Call the refactored parsing function to get phrase and confidence
        parsed_phrase, confidence = parse_single_phrase(ocr_data, min_confidence=0, return_confidence=True)
        if parsed_phrase:
            all_parsed_phrases.append((parsed_phrase, confidence))

    # 3. Verification
    print("\n--- OCR Results ---")
    for phrase, confidence in all_parsed_phrases:
        print(f"- '{phrase}' (Confidence: {confidence:.2f}%)")
    print("---------------------\n")

    assert len(all_parsed_phrases) > 0, "OCR process ran but did not find any ingredients. Check game screen and ROI."


# --- New ROI for Recipe List ---
# This ROI should be configured for the area where the current recipe's
# ingredient list is displayed (typically white text on a dark grey background).
MANUAL_RECIPE_LIST_ROI = {
    "left": 452,    # X coordinate of the top-left corner
    "top": 884,   # Y coordinate of the top-left corner
    "width": 1012,  # Width of the region
    "height": 97, # Height of the region
}


@pytest.mark.skip(reason="Manual test: requires game to be running and ROI to be configured.")
def test_live_ocr_on_recipe_list():
    """
    Captures the recipe list from a live game screen, processes it with OCR,
    and prints the results for manual verification.
    """
    print("\n--- Starting Live OCR Test for Recipe List ---")
    print(f"Capturing region: {MANUAL_RECIPE_LIST_ROI}")

    # 1. Capture the screen region
    recipe_image_pil = capture_region(MANUAL_RECIPE_LIST_ROI)
    assert recipe_image_pil is not None, "Screen capture failed. Is the region valid?"

    # Convert to OpenCV format
    recipe_image_cv = cv2.cvtColor(np.array(recipe_image_pil), cv2.COLOR_RGB2BGR)

    image_to_process = recipe_image_cv # no shear correction for recipe - it's not italic.

    # --- Upscale the image to improve OCR on potentially small text ---
    # A scale factor of 2.0 is a good starting point.
    scale_factor = 2.0
    width = int(image_to_process.shape[1] * scale_factor)
    height = int(image_to_process.shape[0] * scale_factor)
    upscaled_image = cv2.resize(image_to_process, (width, height), interpolation=cv2.INTER_CUBIC)

    # 2. Process the captured image using the non-panel OCR pipeline
    processed_image = binarize_image(upscaled_image, invert_colors=True)

    if processed_image is None or processed_image.size == 0:
        pytest.fail("Image binarization failed.")

    # Use PSM 6 for a single uniform block of text.
    ocr_data = extract_text_from_image(processed_image, psm=6)
    
    # Call the refactored parsing function to get ingredients and their confidences
    parsed_ingredients_with_conf = parse_ingredient_list(ocr_data, min_confidence=0, return_confidence=True)

    # 3. Verification
    print("\n--- OCR Results ---")
    for phrase, confidence in parsed_ingredients_with_conf:
        print(f"- '{phrase}' (Confidence: {confidence:.2f}%)")
    print("---------------------\n")

    assert len(parsed_ingredients_with_conf) > 0, "OCR process ran but did not find any ingredients. Check game screen and ROI."
