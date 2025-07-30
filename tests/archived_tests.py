import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_single_ingredient_tests_legacy():
    """
    DEPRECATED: This is a legacy test case loader for reference.
    It manually discovers single-ingredient tests from a specific subdirectory
    with hardcoded parameters. The current convention-based approach in
    test_ocr_processor.py is more flexible and is the active implementation.
    """
    test_cases = []
    single_ingredient_dir = FIXTURES_DIR / "single_ingredients"
    if single_ingredient_dir.is_dir():
        for image_path in single_ingredient_dir.glob("*.png"):
            # The expected text is the name of the file without the extension.
            expected_text = image_path.stem
    
            test_cases.append(
                pytest.param(
                    image_path,
                    False,  # Assume dark text on light background
                    False,  # Not a panel
                    expected_text,
                    7,      # Default PSM
                    50,     # Default confidence
                    id=f"single_ingredient_{expected_text}"
                )
            )
    return test_cases