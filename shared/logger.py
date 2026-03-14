import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# Agent color map for Rich console output
AGENT_COLORS = {
    "Neo": "bold white",
    "Trinity": "cyan",
    "Morpheus": "green",
    "Oracle": "yellow",
    "Keymaker": "magenta",
    "Tank": "blue",
    "Niobe": "bright_red",
    "Mouse": "bright_green",
    "Smith": "red",
    "Merovingian": "bright_magenta",
    "Architect": "bright_cyan",
}

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "matrix.log"


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Return a configured logger for the given agent."""
    logger = logging.getLogger(f"matrix.{agent_name}")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler with rotation
    LOG_DIR.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)

    # Rich console handler
    console = Console(stderr=True)
    color = AGENT_COLORS.get(agent_name, "white")
    rich_handler = RichHandler(
        console=console,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setFormatter(logging.Formatter(f"[{color}][{agent_name}][/{color}] %(message)s"))
    logger.addHandler(rich_handler)

    return logger
