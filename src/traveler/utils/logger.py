"""
Structured logger for snackPersona.traveler.

Provides a shared ``logger`` instance with console output.
"""

import logging

logger = logging.getLogger("snackPersona.traveler")

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
