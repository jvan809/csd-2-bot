import logging
import sys
from src.config_manager import ConfigManager


def setup_logger(config: ConfigManager, log_file: str = 'bot_activity.log'):
    """Configures and returns a logger for the application."""
    log_level_str = config.get_setting("bot_settings.logging_level", default="INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger('csd2_bot')
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if the function is called more than once
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file, mode='a')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger