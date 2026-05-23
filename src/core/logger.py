"""
src/core/logger.py
Logging setup for SC Dossier.

- RotatingFileHandler → Logs/app.log (5MB max, 3 backups)
- Console output in dev mode (detected via DEV_MODE env var or --dev flag)
- Root logger configured at module load.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def setup_logging(log_file: Path, dev_mode: bool = False) -> None:
    """
    Configure application logging.

    Args:
        log_file: Path to the rotating log file (parent dir must exist).
        dev_mode: If True, also output to stderr at DEBUG level.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Remove any existing handlers to avoid duplicate log entries on re-init
    root.handlers.clear()

    # --- Rotating file handler ---
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_file_formatter())
    root.addHandler(file_handler)

    # --- Console handler (dev mode) ---
    if dev_mode or _is_dev_mode():
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(_console_formatter())
        root.addHandler(console_handler)

    logging.getLogger(__name__).info(
        "Logging initialized. File: %s | Dev mode: %s", log_file, dev_mode or _is_dev_mode()
    )


def _is_dev_mode() -> bool:
    """Auto-detect dev mode via environment variable or CLI flag."""
    return bool(os.environ.get("SCDOSSIER_DEV")) or "--dev" in sys.argv


def _file_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _console_formatter() -> logging.Formatter:
    """Colorized console formatter for dev mode."""
    try:
        import colorama  # optional
        colorama.init()
        COLORS = {
            "DEBUG": colorama.Fore.CYAN,
            "INFO": colorama.Fore.GREEN,
            "WARNING": colorama.Fore.YELLOW,
            "ERROR": colorama.Fore.RED,
            "CRITICAL": colorama.Fore.MAGENTA,
        }

        class ColorFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                color = COLORS.get(record.levelname, "")
                reset = colorama.Style.RESET_ALL
                record.levelname = f"{color}{record.levelname}{reset}"
                return super().format(record)

        return ColorFormatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    except ImportError:
        return logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
