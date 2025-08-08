from typing import List, Tuple
import difflib
import re
import logging

log = logging.getLogger('csd2_bot')


NUMBER_WORDS = {
    'once': 1, 'twice': 2, 'thrice': 3,
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
}


def _parse_step_for_action_and_count(step: str) -> Tuple[str, int]:
    """
    Parses a recipe step to extract the core action and a repetition count.
    Handles formats like "Nuggets (4)" and "Roll twice".
    """
    # Case 1: "Nuggets (4)" - handles one or more digits
    numeric_match = re.search(r'[\(\{}](\d+)[\)\}]', step)
    if numeric_match:
        count = int(numeric_match.group(1))
        action = re.sub(r'\s*\(\d+\)', '', step, flags=re.IGNORECASE).strip()
        return action, count

    # Case 2: "Cut eight times" or "Roll twice"
    step_lower = step.lower()
    # Anchors the match to the end of the string for reliability
    number_word_pattern = r'\b(' + '|'.join(NUMBER_WORDS.keys()) + r')\b(?:\s+times)?$'
    text_match = re.search(number_word_pattern, step_lower)
    if text_match:
        number_word = text_match.group(1)
        count = NUMBER_WORDS[number_word]
        action = step[:text_match.start()].strip()
        if action:
            return action, count

    # Default case: no number found
    return step, 1


def _find_best_match(target: str, options: List[str]) -> dict | None:
    """
    Finds the best match for a target string from a list of options using a multi-criteria scoring model.

    The model uses difflib's sequence matching ratio and adds a bonus if the
    option starts with the same letter as the target. This helps prioritize
    matches that are likely abbreviations or correct but partial OCR reads.

    Args:
        target: The string to find a match for (e.g., a recipe step).
        options: A list of available strings to match against (e.g., ingredients on page).

    Returns:
        A dictionary containing the best match details (including the new 'score'),
        or None if no suitable match is found.
    """
    if not target or not options:
        return None

    # This bonus is added to the ratio if the first letters match. It's calibrated
    # to be roughly equivalent to 1-2 additional matching characters in a typical
    # string, making it a significant but not overpowering factor.
    FIRST_LETTER_BONUS = 0.15

    target_lower = target.lower()
    # SequenceMatcher is efficient for repeated comparisons against a single string.
    matcher = difflib.SequenceMatcher(isjunk=None, b=target_lower)

    best_match_details = None
    highest_score = -1.0
    split_pattern = "[\.\s]+"

    for i, opt in enumerate(options):
        if not opt:
            continue

        opt_lower = opt.lower()
        matcher.set_seq1(opt_lower)
        score = ratio = matcher.ratio()

        # Add a bonus if the first letters match. This helps prioritize
        # abbreviations or partial OCR reads (e.g., "L" for "Lettuce").
        opt_words = re.split(split_pattern, opt_lower)
        target_words = re.split(split_pattern, target_lower)

        for opt_word, target_word in zip(opt_words, target_words):
            if opt_word and target_word and opt_word[0] == target_word[0]:
                score += FIRST_LETTER_BONUS

        if score > highest_score:
            highest_score = score
            best_match_details = {'text': opt, 'index': i, 'ratio': ratio, 'score': score}

    return best_match_details


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
    # Keep parentheses for number parsing, split on other non-alphanumeric chars
    pattern_to_split = r'[^\d\sA-Za-z()]| and '
    for i, step in enumerate(required_steps):
        # Check if a step is long and contains separators, indicating a multi-step instruction.
        if len(step) > multi_step_threshold and re.search(pattern_to_split, step):
            sub_steps = [s.strip() for s in re.split(pattern_to_split, step)]
            for sub_step in sub_steps:
                if sub_step:
                    expanded_steps.append(sub_step)
        elif step:
            expanded_steps.append(step)

    # 2. Parse each step for its action and count, then find the best match.
    all_matches = []
    for step_text in expanded_steps:
        action, count = _parse_step_for_action_and_count(step_text)
        best_match = _find_best_match(action, available_on_page)
        if best_match and best_match['score'] >= match_threshold:
            all_matches.append({
                'count': count,
                'index': best_match['index'],
                # For logging/debugging:
                'original_step': step_text,
                'matched_action': action,
                'matched_ingredient': best_match['text'],
                'score': best_match['score']
            })

    if not all_matches:
        log.debug("No Matches found on this page")
        return []
    
    log.debug(f"Matches Found: {all_matches}")

    # 3. Convert matches to key presses.
    final_keys = []
    for match in all_matches:
        final_keys.extend([input_keys[match['index']]] * match['count'])

    log.debug(f"Fuzzy mapped keys for page: {final_keys}")
    return final_keys
