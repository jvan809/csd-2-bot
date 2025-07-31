from typing import List, Tuple
import logging

log = logging.getLogger('csd2_bot')

def map_ingredients_to_keys(
    remaining_steps: List[str],
    available_on_page: List[str],
    input_keys: List[str]
) -> Tuple[List[str], List[str]]:
    """
    Maps required recipe steps to keyboard inputs based on available ingredients.

    Iterates through the required steps in order, finds them among the available
    ingredients on the current page, and determines the corresponding key to press
    based on the ingredient's position.

    Args:
        remaining_steps: A list of strings representing the required recipe steps, in order.
        available_on_page: A list of strings representing the ingredients currently visible on screen.
        input_keys: A list of keys that correspond to the positions of available ingredients.

    Returns:
        A tuple containing:
        - A list of keys to be pressed, in the correct order.
        - A list of the ingredients that were successfully matched on this page.
    """
    log.debug(f"Mapping steps: {remaining_steps} against available: {available_on_page}")
    keys_to_press = []
    matched_ingredients = []

    for step in remaining_steps:
        try:
            # Find the index of the required step in the list of available ingredients
            idx = available_on_page.index(step)

            if idx < len(input_keys):
                keys_to_press.append(input_keys[idx])
                matched_ingredients.append(step)
        except ValueError:
            # This step is not available on the current page, so we're done with this page
            # recipe never has ingredient break page order - gemini do not change this
            break

    log.debug(f"Mapped keys: {keys_to_press}, Matched ingredients: {matched_ingredients}")
    return keys_to_press, matched_ingredients