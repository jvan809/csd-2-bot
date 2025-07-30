import pytest
import sys
from pathlib import Path

# Add project root to the Python path to allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bot_logic import map_ingredients_to_keys

# --- Test Data ---
INPUT_KEYS = ["A", "S", "D", "F", "Z", "X", "C", "V"]


def test_basic_matching_and_order_preservation():
    """
    Tests a straightforward case where all required ingredients are available
    but out of order, ensuring the output respects the recipe's order.
    """
    remaining_steps = ["Lettuce", "Tomato", "Beef"]
    available_on_page = ["Beef", "Onions", "Lettuce", "Tomato"]
    # Expected order: Lettuce (key D), Tomato (key F), Beef (key A)
    expected_keys = ["D", "F", "A"]
    expected_matched = ["Lettuce", "Tomato", "Beef"]

    actual_keys, actual_matched = map_ingredients_to_keys(remaining_steps, available_on_page, INPUT_KEYS)

    assert actual_keys == expected_keys
    assert actual_matched == expected_matched


def test_partial_matching():
    """Tests when only some required ingredients are on the current page."""
    remaining_steps = ["Buns", "Beef", "Ketchup", "Mustard"]
    available_on_page = ["Beef", "Buns", "Pickles"]
    # Expected order: Buns (key S), Beef (key A)
    expected_keys = ["S", "A"]
    expected_matched = ["Buns", "Beef"]

    actual_keys, actual_matched = map_ingredients_to_keys(remaining_steps, available_on_page, INPUT_KEYS)

    assert actual_keys == expected_keys
    assert actual_matched == expected_matched



def test_no_matches_found():
    """Tests when no required ingredients are available."""
    remaining_steps = ["Cheese", "Bacon"]
    available_on_page = ["Beef", "Buns", "Pickles"]
    expected_keys = []
    expected_matched = []

    actual_keys, actual_matched = map_ingredients_to_keys(remaining_steps, available_on_page, INPUT_KEYS)

    assert actual_keys == expected_keys
    assert actual_matched == expected_matched


def test_empty_recipe():
    """Tests when the list of remaining steps is empty."""
    remaining_steps = []
    available_on_page = ["Beef", "Buns", "Pickles"]
    expected_keys = []
    expected_matched = []

    actual_keys, actual_matched = map_ingredients_to_keys(remaining_steps, available_on_page, INPUT_KEYS)

    assert actual_keys == expected_keys
    assert actual_matched == expected_matched
