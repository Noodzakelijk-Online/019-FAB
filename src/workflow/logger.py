import logging
import os

class AppLogger:
    """A centralized logging utility for the application."""

    def __init__(self, name: str = "automated_bookkeeping", log_level: str = "INFO", log_file: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level.upper())

        # Clear existing handlers to prevent duplicate logs
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(log_level.upper())
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        # File handler (optional)
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(log_file)
            fh.setLevel(log_level.upper())
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def get_logger(self) -> logging.Logger:
        return self.logger

# Example Usage (can be used directly or instantiated)
# logger = AppLogger(log_file="app.log").get_logger()
# logger.info("Application started")


