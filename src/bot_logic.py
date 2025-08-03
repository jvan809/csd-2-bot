from typing import List, Tuple
import difflib
import re
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
            # theoretically we could break here, because the required ingredients are always sorted by page order
            # in practice we'll continue in case of unmmatched ingredients.
            continue

    log.debug(f"Mapped keys: {keys_to_press}, Matched ingredients: {matched_ingredients}")
    return keys_to_press, matched_ingredients


def _find_best_match(target: str, options: List[str]) -> dict | None:
    """
    Finds the best match for a target string from a list of options using difflib.

    Args:
        target: The string to find a match for (e.g., a recipe step).
        options: A list of available strings to match against (e.g., ingredients on page).

    Returns:
        A dictionary containing the best match details, or None if no suitable match is found.
    """
    if not target or not options:
        return None

    # SequenceMatcher is efficient for repeated comparisons against a single string.
    matcher = difflib.SequenceMatcher(isjunk=None, a=target.lower())
    
    # Find the best match using a generator expression and max() for conciseness.
    # We map each option to a tuple of (ratio, option, index).
    # max() will find the tuple with the highest ratio.
    try:
        best_ratio, best_match_text, best_match_idx = max(
            (matcher.set_seq2(opt.lower()), matcher.ratio(), opt, i)
            for i, opt in enumerate(options) if opt
        )[1:] # [1:] to discard the None from set_seq2
    except ValueError:
        # This occurs if the options list is empty or contains only empty strings.
        return None

    return {'text': best_match_text, 'index': best_match_idx, 'ratio': best_ratio}


def fuzzy_map_ingredients_to_keys(
    remaining_steps: List[str],
    available_on_page: List[str],
    input_keys: List[str],
    config: dict
) -> Tuple[List[str], List[str]]:
    """
    Maps recipe steps to keyboard inputs using fuzzy string matching.

    This function handles simple ingredient names, abbreviations (e.g., "SJ. Tuna"),
    and long, multi-step instructions by breaking them down.

    Args:
        remaining_steps: The list of required recipe steps.
        available_on_page: The list of ingredients visible on screen.
        input_keys: The list of keys corresponding to ingredient positions.
        config: A dictionary of fuzzy matching settings from the config manager.

    Returns:
        A tuple containing:
        - A list of keys to press.
        - A list of the original recipe steps that were successfully matched.
    """
    multi_step_threshold = config.get('multi_step_char_threshold', 20)
    match_threshold = config.get('fuzzy_match_threshold', 0.6)

    # 1. Expand multi-step instructions into individual, trackable steps.
    expanded_steps = []
    for i, step in enumerate(remaining_steps):
        # Check if a step is long and contains commas, indicating a multi-step instruction.
        if len(step) > multi_step_threshold and re.match('[,.]', step):
            sub_steps = [s.strip() for s in re.split('[,.]', step)]
            for sub_step in sub_steps:
                if sub_step:
                    expanded_steps.append({'text': sub_step, 'original_idx': i, 'original_step': step})
        else:
            expanded_steps.append({'text': step, 'original_idx': i, 'original_step': step})

    # 2. Find the best match for each expanded step.
    all_matches = []
    for expanded_step in expanded_steps:
        best_match = _find_best_match(expanded_step['text'], available_on_page)
        if best_match and best_match['ratio'] >= match_threshold:
            # Combine the recipe step info with its best match info.
            all_matches.append({**expanded_step, **best_match})

    if not all_matches:
        return [], []

    # 3. Sort matches by original recipe order, then by match quality (ratio) descending.
    # This ensures we process ingredients in the correct order and prefer better matches.
    all_matches.sort(key=lambda m: (m['original_idx'], -m['ratio']))

    # 4. De-duplicate and finalize the key presses.
    # An available ingredient can only be used once per page.
    final_keys = []
    final_matched_original_steps = set()
    used_available_indices = set()

    for match in all_matches:
        if match['index'] not in used_available_indices:
            if match['text'] and match['index'] < len(input_keys):
                final_keys.append(input_keys[match['index']])
                final_matched_original_steps.add(match['original_step'])
                used_available_indices.add(match['index'])

    log.debug(f"Fuzzy mapped keys: {final_keys}, Matched original steps: {list(final_matched_original_steps)}")
    return final_keys, list(final_matched_original_steps)
