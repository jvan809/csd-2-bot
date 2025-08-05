---
goal: Implementation Plan for the CSD2 Bot MVP
version: 1.0
date_created: 2025-07-30
last_updated: 
owner: AI Assistant (for User)
tags: ['feature', 'app', 'automation', 'game', 'python', 'ai', 'mvp']
---

# Introduction

This plan outlines the implementation steps for creating the Minimum Viable Product (MVP) of the `csd2` bot. The goal is to build a Python-based application for Windows that automates gameplay by reading recipe information from the screen using OCR and emulating the necessary keyboard inputs to complete the recipe.

**Known Foods that don't work** 
*Extra step handling* Beef wellington, steamed momos
*timing* creme brulee, beer (both kinds)

## 1. Requirements & Constraints

- **REQ-001**: The bot shall run on the Windows operating system.
- **REQ-002**: The bot shall be written in Python.
- **REQ-003**: The bot shall read the required ingredients from the game screen in real-time.
- **REQ-004**: The bot shall emulate keyboard presses corresponding to the identified ingredients and cooking actions.
- **REQ-005**: The bot shall log its actions (e.g., recipe identified, keys pressed, errors).
- **REQ-006**: The bot shall support handling all ~200 foods in the game with minimal hardcoding of specific recipes.
- **REQ-008**: The bot must execute ingredient key presses in the order specified by the recipe, not the order they appear on the screen.
- **REQ-007**: The project shall include a `README.md` file with clear setup and usage instructions.
- **CON-001**: The game does not provide a public API for programmatic interaction.
- **CON-002**: For the MVP, the bot will assume a fixed, full-screen resolution. Resilience to different window sizes is deferred.
- **CON-003**: The bot should perform screen capture one time per page of ingredients.
- **CON-004**: OCR must handle text on varied backgrounds (black text on white, white text on a fixed knife background).
- **GUD-001**: Implement a 'setup' phase to identify and store bounding box coordinates for OCR regions.
- **GUD-002**: Use `pyautogui`'s mouse-based failsafe as a "panic button" to stop bot operation.
- **GUD-003**: Favor a modular design where screen reading, decision logic, and input emulation are separated.
- **GUD-004**: Abstract external library calls for screen capture and key presses into wrapper functions.
- **GUD-005**: To prevent infinite loops, the bot shall attempt a maximum of three pages of ingredients per recipe (one initial view plus two page-turns).
- **GUD-006**: If the initial OCR of a recipe fails (i.e., no text is found), the bot should enter a retry loop, attempting to read the screen again after a short delay until successful.

## 2. Implementation Steps

### Implementation Phase 1: Project Setup & Core Utilities

- GOAL-001: Establish the project structure, manage dependencies, and create foundational utility modules for configuration, logging, and I/O.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Create the project directory structure: `/src`, `/plan`, `/tests`, `/assets/templates`. |X|2025-07-29|
| TASK-002 | Create and populate `requirements.txt` with `mss`, `Pillow`, `opencv-python`, `pytesseract`, and `pyautogui`. |X|2025-07-29|
| TASK-003 | Create `src/config_manager.py` to load, access, and save settings from `config.json`, including a default structure. |X|2025-07-29|
| TASK-004 | Create `src/logger_setup.py` to configure a file logger for application events and errors. |X|2025-07-29|
| TASK-005 | Create `src/input_handler.py` with a wrapper function `press_key(key)` for `pyautogui.press()`. |X|2025-07-29|
| TASK-006 | Create `src/screen_capture.py` with a wrapper function `capture_region(roi)` using `mss`. |X|2025-07-29|
| TASK-007 | Create `main.py` with a basic application entry point and main loop structure, including the `pyautogui` failsafe. |X|2025-07-29|
| TASK-008 | Create `README.md` and populate it with installation and usage instructions as per `REQ-007`. |X|2025-07-29|

### Implementation Phase 2: Screen Analysis & OCR (with Integrated Testing)

- GOAL-002: Implement and verify the logic to capture, process, and extract text from screen regions.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Create `src/ocr_processor.py`. | X | 2025-07-29 |
| TASK-010 | In `src/ocr_processor.py`, implement the core image processing and text extraction functions (`normalize_image`, `binarize_image`, `extract_text_from_image`, etc.). | X | 2025-07-29 |
| TASK-011 | In `src/ocr_processor.py`, implement `find_ingredient_boxes(panel_image)` using OpenCV contour detection to programmatically find ingredient boxes. | X | 2025-07-29 |
| TASK-012 | In `src/ocr_processor.py`, implement the text parsing functions (`parse_single_phrase`, `parse_ingredient_list`). | X | 2025-07-29 |
| TASK-013 | Add `pytest` to `requirements.txt` for test execution. | X | 2025-07-29 |
| TASK-014 | Create test fixture directory `tests/fixtures/` and populate with sample images and corresponding `.txt` files with expected output. | X | 2025-07-29 |
| TASK-015 | Create `tests/test_ocr_processor.py` with an end-to-end pipeline test that loads fixtures, runs the full OCR process, and asserts the output matches the expected text. | X | 2025-07-29 |

### Implementation Phase 3: Core Bot Logic & Integration

- GOAL-003: Integrate all modules to create the primary gameplay loop: read, decide, and act.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016 | Create `src/bot_logic.py`. | X | 2025-07-30 |
| TASK-017 | In `src/bot_logic.py`, implement `map_ingredients_to_keys(remaining_steps, available_on_page, input_keys)`. The function must iterate through `remaining_steps` in order, find a perfect match in `available_on_page`, and map it to the correct keys from `input_keys` based on the available ingredient's position. It should return the sequence of keys to press and the list of matched ingredients. | X | 2025-07-30 |
| TASK-018 | Create `tests/test_bot_logic.py` to unit test the decision-making module. | X | 2025-07-30 |
| TASK-019 | In `test_bot_logic.py`, write unit tests for `map_ingredients_to_keys` with mock data to ensure correct key sequences are generated. | X | 2025-07-30 |
| TASK-020 | In `main.py`, implement the main gameplay loop. The sequence should be: <br>1. **Load Config**: Load all ROIs (`recipe_list_roi`, `ingredient_panel_roi`) and control keys (`input_keys`, `page_turn_key`, `confirm_key`) from `config.json`. <br>2. **Wait for Recipe**: Start a retry loop (per `GUD-006`) to capture the `recipe_list_roi` and use OCR to get the full list of `remaining_steps`. <br>3. **Ingredient Page Loop**: While `remaining_steps` is not empty (and page turns < 2): <br>   a. Capture the `ingredient_panel_roi` and get the `available_on_page`. <br>   b. Call `map_ingredients_to_keys` to get keys to press and matched ingredients. <br>   c. Execute key presses and update `remaining_steps`. <br>   d. If steps remain, press the page-turn key and increment a counter. <br>4. **Serve Order**: Once the loop is complete, press the confirm/serve key. | X | 2025-07-30 |
| TASK-021 | Integrate the logger throughout the application to log key decisions, actions, and errors. | X | 2025-07-31 |

### Implementation Phase 4: Calibration & Setup

- GOAL-004: Develop a one-time setup script to pre-calculate the static positions of all UI elements, including individual ingredient slots, and generate a mask to handle rounded corners, optimizing the main loop.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-022 | Create a `setup.py` script. The script should instruct the user to have the game open (full-screen) and visible. | X | 2025-08-02 |
| TASK-023 | In `setup.py`, set up code to allow the user to determine `ingredient_panel_roi` and `recipe_list_roi`. | X | 2025-08-02 |
| TASK-024 | In `setup.py`, instruct the user to display a screen with at least 5 ingredients. Run contour detection within the `ingredient_panel_roi` to find the 5+ individual ingredient boxes, and extrapolate up to 8 total | X | 2025-08-02 |
| TASK-025 | For each of the 8 ingredient boxes, calculate its relative ROI (relative to the `ingredient_panel_roi`). From one contour, generate a corner mask image using `cv2.convexHull` and save it to `/assets/masks/ingredient_mask.png`. | X | 2025-08-02 |
| TASK-026 | In `setup.py`, use the `config_manager` to write all calculated ROIs (main panels, a list of 8 individual relative slot ROIs) and the mask path into `config.json`. | X | 2025-08-02 |
| TASK-027 | Refactor `OcrProcessor.process_ingredient_panel_roi` to accept the main `ingredient_panel_roi` and the list of `relative_ingredient_slot_rois`. | X | 2025-08-02 |
| TASK-028 | In the refactored `process_ingredient_panel_roi`, perform a **single screen capture** of the `ingredient_panel_roi`. Then, loop through each `relative_slot_roi` to **slice** the captured image into individual slot images. For each slice, check for an active ingredient, apply the pre-loaded corner mask, and run the OCR pipeline. | X | 2025-08-02 |
| TASK-029 | In `CSD2Bot` (`main.py`), update the `_process_recipe` method to load the `ingredient_panel_roi` and `relative_ingredient_slot_rois` from the config and pass them to the updated `ocr.process_ingredient_panel_roi` method. | X | 2025-08-02 |

### Implementation Phase 5: Page-Aware Recipe Processing

- GOAL-005: Enhance the bot to understand which recipe steps belong to which ingredient page, and update the core logic to process recipes page-by-page, preventing incorrect early matches.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-030 | In `setup.py`, add a new interactive step to have the user define the pixel positions for the 2nd and 3rd page indicator boxes next to the recipe list by clicking them (using similar logic to the panel corners). | X | 2025-08-03 |
| TASK-032 | In `setup.py`, add a step to have the user navigate to a recipe with at least 6 "normal" steps to programmatically find the 10 recipe slot ROIs and key vertical coordinates (top/bottom of rows, top/bottom of panel). | X | 2025-08-03 |
| TASK-033 | In `setup.py`, save all new ROIs (page indicators, recipe slots) and vertical coordinates into `config.json` under a new `recipe_layout` object. | X | 2025-08-03 |
| TASK-034 | Refactor `OcrProcessor.process_recipe_list_roi` to implement the new page-aware logic. It must now return a `list[list[str]]` of size 4, representing steps for page 1, 2, 3, and other steps. Note: 'other steps' mean any steps that do not follow the typical format, and are to be reutrned from this function as a single string to be processed by the bot logic. | X | 2025-08-04 |
| TASK-035 | In the refactored `process_recipe_list_roi`, create helper functions: `_get_active_pages` (checks indicator colors), `_ocr_recipe_slots` (uses the 10 slot ROIs to get normal steps, if any step fails ocr the failing image should be saved and a warning should be displayed using log.warning()), and `_ocr_extra_region` (uses vertical coordinates to find instructions extra to the normal grid ). | X | 2025-08-04 |
| TASK-036 | Refactor `CSD2Bot._process_recipe` in `main.py` to remove the flat `remaining_steps` logic. The new logic will process the recipe page by page. | | |
| TASK-037 | In the new `_process_recipe`, iterate from page 1 to 3. For each page: <br> a. Get the steps for the current page from the OCR data structure. <br> b. If steps exist, call the mapping function and press keys. <br> c. Check if the *next* page is active using a pixel check. If so, press the page turn key. | | |
| TASK-038 | In `_process_recipe`, after handling pages 1-3, process the extra instructions from the OCR data structure. | | |
| TASK-039 | Update `fuzzy_map_ingredients_to_keys` to no longer need to track `original_step`. It will receive a simple list of steps for the current page and should return keys and the text of the ingredients it matched. The main loop no longer needs to remove steps. | | |




## 3. Alternatives

- **ALT-001**: Hard-coding screen coordinates: This was rejected because it is not resilient to changes in game window size or resolution, violating `CON-002`. The dynamic setup phase is more robust.
- **ALT-002**: Using a different OCR engine: Tesseract was chosen due to its maturity, Python support via `pytesseract`, and offline capabilities. Other cloud-based OCR services were rejected as they would introduce internet dependencies.

## 4. Dependencies

- **DEP-001**: Python 3.x runtime environment.
- **DEP-002**: Tesseract OCR Engine system executable.
- **DEP-003**: Python library: `mss` (for screen capture).
- **DEP-004**: Python library: `Pillow` (for image manipulation).
- **DEP-005**: Python library: `opencv-python` (for image processing and template matching).
- **DEP-006**: Python library: `pytesseract` (for Tesseract OCR interface).
- **DEP-007**: Python library: `pyautogui` (for keyboard emulation and failsafe).

## 5. Files

- **FILE-001**: `/plan/feature-csd2-bot-1.md` (This file)
- **FILE-002**: `/main.py` (Main application entry point)
- **FILE-003**: `/setup.py` (One-time calibration script)
- **FILE-004**: `/requirements.txt` (Project dependencies)
- **FILE-005**: `/config.json` (Stores ROIs and settings)
- **FILE-006**: `/src/config_manager.py` (Handles configuration data)
- **FILE-007**: `/src/logger_setup.py` (Handles logging setup)
- **FILE-008**: `/src/screen_capture.py` (Wrapper for screen grabbing)
- **FILE-009**: `/src/input_handler.py` (Wrapper for keyboard emulation)
- **FILE-010**: `/src/ocr_processor.py` (Handles image processing and text extraction)
- **FILE-011**: `/src/bot_logic.py` (Contains the core decision-making logic)
- **FILE-012**: `/README.md` (User-facing setup and usage instructions)

## 6. Testing

- **TEST-001**: Unit tests for `ocr_processor.py` using a set of pre-captured static screenshots from `/tests/fixtures` to ensure reliable text extraction.
- **TEST-002**: Unit tests for `bot_logic.py` using mock ingredient lists to verify the key-mapping logic is correct.
- **TEST-003**: Integration test for `setup.py` to confirm it correctly identifies template images and writes a valid `config.json`.
- **TEST-004**: Manual end-to-end test running the bot against the live game to verify timing, accuracy, and the failsafe mechanism.

## 7. Risks & Assumptions

- **RISK-001**: OCR accuracy may be insufficient out-of-the-box and could require extensive image pre-processing tuning for different in-game text backgrounds.
- **RISK-002**: Future game patches may alter UI elements, breaking the template matching in the `setup.py` script and requiring new template images.
- **RISK-003**: The performance of the capture -> process -> input pipeline may be too slow for the game's real-time demands, leading to missed orders.
- **RISK-004**: The manual setup process (installing Python, Tesseract, and packages) may be too complex for non-technical users, hindering adoption.
- **ASSUMPTION-001**: The performance of the capture -> process -> input pipeline in Python will be fast enough to meet the game's real-time demands.
- **ASSUMPTION-002**: The geometric relationship between reference UI elements and the OCR regions is constant across all supported resolutions.

## 8. Related Specifications / Further Reading

- csd2 Bot MVP Specification