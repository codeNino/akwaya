import logging
import sys

class ColoredFormatter(logging.Formatter):
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

class AppLogger:
    def __init__(self, service_name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(service_name)
        self._logger.setLevel(level)

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.propagate = False

    def __call__(self) -> logging.Logger:
        return self._logger
