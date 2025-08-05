from typing import List, Tuple
import difflib
import re
import logging

log = logging.getLogger('csd2_bot')


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
    required_steps: List[str],
    available_on_page: List[str],
    input_keys: List[str],
    config: dict
) -> List[str]:
    """
    Maps recipe steps for a single page to keyboard inputs using fuzzy string matching.

    This function handles simple ingredient names as well as long, multi-step 
    instructions by breaking them down. It returns a list of keys to press
    in the correct order for the current page.

    Args:
        required_steps: The list of required recipe steps for the current page.
        available_on_page: The list of ingredients visible on screen.
        input_keys: The list of keys corresponding to ingredient positions.
        config: A dictionary of fuzzy matching settings.

    Returns:
        A list of keys to press.
    """
    multi_step_threshold = config.get('multi_step_char_threshold', 20)
    match_threshold = config.get('fuzzy_match_threshold', 0.6)

    # 1. Expand multi-step instructions into individual, trackable steps.

    expanded_steps = []
    for i, step in enumerate(required_steps):
        # Check if a step is long and contains separators, indicating a multi-step instruction.
        if len(step) > multi_step_threshold and re.search('[,.]', step):
            sub_steps = [s.strip() for s in re.split('[,.]', step)]
            for sub_step in sub_steps:
                if sub_step:
                    expanded_steps.append({'text': sub_step, 'original_idx': i})
        else:
            expanded_steps.append({'text': step, 'original_idx': i})

    # 2. Find the best match for each expanded step.
    all_matches = []
    for expanded_step in expanded_steps:
        best_match = _find_best_match(expanded_step['text'], available_on_page)
        if best_match and best_match['ratio'] >= match_threshold:
            all_matches.append({**expanded_step, **best_match})

    if not all_matches:
        log.debug("No Matches found on this page")
        return []
    
    log.debug(f"Matches Found: {all_matches}")

    # 3. Sort matches by original recipe order, then by match quality (ratio) descending.
    all_matches.sort(key=lambda m: (m['original_idx'], -m['ratio']))

    # 4. Convert options to key presses. 
    # Note: duplicates happen somtimes and are fine
    final_keys = [input_keys[match['index']] for match in all_matches if match['text']]


    log.debug(f"Fuzzy mapped keys for page: {final_keys}")
    return final_keys
