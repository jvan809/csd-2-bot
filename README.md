# CSD2 Bot - MVP

This project is a Python-based bot for the game "Cook, Serve, Delicious! 2!!" that automates gameplay by reading recipes from the screen and emulating keyboard inputs.

This MVP focuses on reading a single active recipe and executing its steps.

## Features

- **Screen Reading**: Uses Tesseract OCR to read recipe and ingredient text from the game window.
- **Dynamic Calibration**: A setup script automatically finds the game's UI elements to work with different window sizes and resolutions.
- **Keyboard Emulation**: Simulates key presses to prepare food.
- **Failsafe**: Move the mouse to the top-left corner of the screen to immediately stop the bot.

## Installation

Follow these steps to set up the bot on your Windows machine.

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
    - A `config.json` file will be created automatically on first run.
    - If Tesseract was not installed to the default location, open `config.json` and update the `tesseract_path` to point to your `tesseract.exe`.

## Usage

### 1. One-Time Calibration

Before running the bot for the first time, you must run the calibration script.

1.  Launch "Cook, Serve, Delicious! 2!!".
2.  Ensure the game window is visible on your screen.
3.  Run the setup script from your terminal:
    ```sh
    python setup.py
    ```
    This will find the necessary UI elements on the screen and save their coordinates to `config.json`.

### 2. Running the Bot

Once calibration is complete, you can run the bot.

1.  Launch the game.
2.  Run the main script:
    ```sh
    python main.py
    ```
3.  The bot will now be active. To stop it, either press `Ctrl+C` in the terminal or move your mouse to the top-left corner of the screen.

## Logging

The bot's activity, including recognized recipes, actions taken, and any errors, is logged to `bot_activity.log`.