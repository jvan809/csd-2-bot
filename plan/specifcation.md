---
title: csd2 Bot MVP Specification
version: 1.0
date_created: 2025-07-29
owner: AI Assistant (for User)
tags: [app, automation, game, python, ai, mvp]
---

# Introduction

This specification outlines the Minimum Viable Product (MVP) for a Python-based Windows script designed to automate gameplay in the offline game "csd2". The primary goal of this MVP is to develop a bot capable of reading the current food recipe displayed on the screen and accurately executing the corresponding ingredient key presses in real-time. This project serves as a learning vehicle for AI and Python development, focusing on screen reading (OCR) and keyboard input emulation.

## 1. Purpose & Scope

The purpose of this specification is to define the core requirements and technical approach for the `csd2` bot's MVP. The scope is strictly limited to identifying and responding to the *currently displayed recipe* at the bottom and right of the game screen. Future phases will involve expanding to handle multiple dockets on the left side of the screen and managing holding stations at the top. The bot will operate solely on a Windows desktop environment, running locally on the user's machine, without any internet connectivity requirements for its operation.

## 2. Definitions

* **MVP**: Minimum Viable Product.
* **OCR**: Optical Character Recognition; the technology used to convert images of text into machine-encoded text.
* **ROI**: Region of Interest; a specific area of an image or screen selected for processing.
* **csd2**: Cook, Serve, Delicious! 2!!, the game targeted for automation.

## 3. Requirements, Constraints & Guidelines

-   **REQ-001**: The bot shall run on the Windows operating system.
-   **REQ-002**: The bot shall be written in Python.
-   **REQ-003**: The bot shall read the required ingredients from the game screen in real-time.
-   **REQ-004**: The bot shall emulate keyboard presses corresponding to the identified ingredients and cooking actions.
-   **REQ-005**: The bot shall log its actions (e.g., recipe identified, keys pressed, errors).
-   **REQ-006**: The bot shall support handling all ~200 foods in the game with minimal hardcoding of specific recipes.
-   **CON-001**: The game does not provide a public API for programmatic interaction.
-   **CON-002**: OCR must be resilient to different game window sizes.
-   **CON-003**: The bot should perform screen capture one time per page of ingredients.
-   **CON-004**: OCR must handle text on varied backgrounds (black text on white, white text on a fixed knife background).
-   **GUD-001**: Implement a 'setup' phase to identify and store bounding box coordinates for OCR regions, leveraging static UI elements (e.g., purple boxes) for scaling.
-   **GUD-002**: Use `pyautogui`'s mouse-based failsafe as a "panic button" to stop bot operation.
-   **GUD-003**: Favor a modular design where screen reading, decision logic, and input emulation are separated.
-   **GUD-004**: Abstract external library calls for screen capture and key presses into wrapper functions.

## 4. Interfaces & Data Contracts

### Internal Data Structures:

-   **Recipe Representation (Ephemeral)**: A list of strings to hold the currently parsed recipe details.
    ```python
    # Example structure for a parsed recipe (bottom)
    required_steps = ['Oil', 'Onions', 'G.Peppers', 'R.Peppers', 'Y.Peppers', 'Beef Faj.']
    # Example for available ingredients (right)
    required_steps = ['Oil', 'Onions', 'G.Peppers', 'R.Peppers', 'Y.Peppers', 'Beef', 'Chicken', 'Shrimp']
    ```

-   **Configuration Data (Persistent)**: A file (e.g., JSON, TOML) storing OCR region bounding box coordinates and other static settings.
    ```jsonc
    {
      // Dynamically populated by the setup script
      "ocr_regions": {
        "current_recipe_name": {"x": 100, "y": 700, "width": 500, "height": 50},
        "current_ingredients": {"x": 100, "y": 750, "width": 800, "height": 100}
      },
      // User-configurable settings
      "bot_settings": {
        "tesseract_path": "C:/Program Files/Tesseract-OCR/tesseract.exe",
        "enable_failsafe": true
      },
      // Static data for the setup script
      "controls": {
        "input_keys" : ["A","S","D","F","Z","X","C","V"],
        "confirm_key" : "Enter"
      }
    }
    ```

## 5. Acceptance Criteria

-   **AC-001**: Given a game screen displaying a single recipe, When the bot is activated, Then the bot shall correctly identify the required ingredients and available ingredients
-   **AC-002**: Given a correctly identified list of ingredients, When the bot processes the ingredients, Then the bot shall execute the correct sequence of key presses for those ingredients and the final cooking action.
-   **AC-003**: Given a running bot, When the mouse cursor is moved to the top-left corner of the screen, Then the bot's input emulation shall immediately cease.
-   **AC-004**: The bot shall produce log files detailing recognized recipes, executed actions, and any encountered errors.
-   **AC-005**: Given the game is running, When the `setup.py` script is executed, Then a valid `config.json` file with correct screen coordinates shall be created.

## 6. Test Automation Strategy

-   **Test Levels**: Unit (for OCR processing, key mapping), Integration (screen capture to key press pipeline).
-   **Frameworks**: Python's `unittest` or `pytest`.
-   **Test Data Management**: Use pre-captured screenshots (static image files) for testing OCR and image processing logic without live game interaction.
-   **CI/CD Integration**: Not applicable for local, single-user MVP, but good practice to consider for future expansion.
-   **Coverage Requirements**: Aim for high test coverage on core parsing and mapping logic.
-   **Performance Testing**: Manual observation and basic timing measurements for key press execution speed.

## 7. Rationale & Context

The decision to focus on a single recipe for the MVP stems from the need to validate core technical challenges (robust OCR, real-time input) first. Avoiding persistent recipe storage simplifies the data model significantly, as all necessary information for the current task is present on-screen. The chosen tech stack (Python, `mss`, `OpenCV`, `Tesseract`, `pyautogui`) provides a balance of performance, flexibility, and ease of use for Windows-based automation. The 'setup' phase addresses the constraint of varying window sizes by allowing dynamic calculation of OCR regions without requiring per-resolution hardcoding.

## 8. Dependencies & External Integrations

### Technology Platform Dependencies
-   **PLT-001**: Python 3.x runtime environment (specific minor version TBD during development).
-   **PLT-002**: Windows Operating System.

### Third-Party Libraries (Python):
-   `mss`: For efficient and fast screen capturing, especially for specific regions.
-   `Pillow`: For basic image manipulation.
-   `OpenCV-Python`: For advanced image processing, color filtering, and potentially template matching for robust ROI detection.
-   `Pytesseract`: Python wrapper for the Tesseract OCR engine.
-   `PyAutoGUI`: For keyboard input emulation and the built-in failsafe mechanism.
-   `json`: For configuration file parsing (built-in).
-   `logging`: Python's built-in module for application logging.

### External Systems
-   **EXT-001**: Tesseract OCR Engine (installed as a system executable) - Required by `Pytesseract` for OCR functionality.

## 9. Examples & Edge Cases

```python
# Example of ephemeral recipe data after OCR
required_steps = ['Oil', 'Onions', 'G.Peppers', 'R.Peppers', 'Y.Peppers', 'Beef Faj.']

# Example of OCR region definition (simplified)
# These coordinates would be dynamically determined in the setup phase
recipe_name_roi = (100, 700, 500, 50) # (x, y, width, height)
ingredients_roi = (100, 750, 800, 100)

# Edge Case: OCR Misinterpretation
# If OCR reading fails such that the required and available ingredients have no overlap, no actions should be taken. 
#  Initial solution is direct string matching, with logging
# to identify frequent misinterpretations for later fine-tuning of OCR.

# Edge Case: Game Window Movement/Resizing
# Handled by the setup phase which recalculates ROI based on reference UI elements.
# If reference UI elements are not found, the setup process should fail gracefully
# and prompt the user for manual calibration or re-launch.