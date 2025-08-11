# CSD2 Bot

This project is a Python-based bot for the game "Cook, Serve, Delicious! 2!!" that automates gameplay by reading recipes from the screen and emulating keyboard inputs.
Currently the bot only activates when there is a recipe on screen, and does not do choose which foods to make. 

## Features

- **Screen Reading**: Uses Tesseract OCR to read recipe and ingredient text from the game window.
- **Keyboard Emulation**: Simulates key presses to prepare food.
- **Dynamic Calibration**: A setup script automatically finds the game's UI elements to work with different window sizes and resolutions.
- **Failsafe**: Bot only presses keys - no mouse movement. Pyautogui failsafe doesn't seem to work

## Installation

I haven't actually tried this on any other machine - May or may not work. 

### 1. Prerequisites

- **Python 3.9+**: Make sure you have Python installed. You can download it from [python.org](https://www.python.org/downloads/). During installation, ensure you check the box that says "Add Python to PATH".
- **Tesseract OCR Engine**: This is required for the text recognition to work.
    - Download the installer from the [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) page.
    - During installation, note the installation path (e.g., `C:\Program Files\Tesseract-OCR`). You will need this path.
    - **Important**: You must add the Tesseract installation directory to your system's `PATH` environment variable.

### 2. Project Setup

1.  **Clone the repository:**
    ```sh
    git clone <repository-url>
    cd csd-2-bot
    ```

2.  **Install Python dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3.  **Configure the bot:**
    Before running the bot for the first time, you must run the calibration script.
    1. Launch the game
    2. In Options > Gameplay, Turn ON large ingredient font. 
    3. Run setup.py
    4. Follow instructions in terminal and on top left of screenshots

    - A `config.json` file will be created automatically on first run.
    - If Tesseract was not installed to the default location, open `config.json` and update the `tesseract_path` to point to your `tesseract.exe`.

## Usage

Once calibration is complete, you can run the bot.

1.  Launch the game.
2.  Run main.py
3.  The bot should post in the terminal that it is active. To stop it, press `Ctrl+C` in the terminal

## Logging

The bot's activity, including recognized recipes, actions taken, and any errors, is logged to `bot_activity.log`. Logging level can be adjusted in the config.
