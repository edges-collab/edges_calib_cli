"""Simple utilities for use elsewhere in the package."""
import functools
import logging
import numpy as np
import time
import u3
from questionary import ValidationError, Validator

from .config import config

logger = logging.getLogger(__name__)


def singleton(cls):
    """Make a class a Singleton class (only one instance)."""

    @functools.wraps(cls)
    def wrapper_singleton(*args, **kwargs):
        if not wrapper_singleton.instance:
            wrapper_singleton.instance = cls(*args, **kwargs)
        return wrapper_singleton.instance

    wrapper_singleton.instance = None
    return wrapper_singleton


def power_handler(signum, frame):
    """Switch off the 48V sp4t power supply controller while detecting ctrl+C."""
    logger.warning("Ctrl+C detected exiting calibration")
    config.p.terminate()
    config.e.terminate()
    config.u3io.getFeedback(u3.BitStateWrite(4, 1))
    config.u3io.getFeedback(u3.BitStateWrite(5, 1))
    config.u3io.getFeedback(u3.BitStateWrite(6, 1))
    config.u3io.getFeedback(u3.BitStateWrite(7, 1))
    time.sleep(1)
    logger.warning("Exiting cleanly...")
    exit(signum)


def int_validator(minval=-np.inf, maxval=np.inf):
    """Return a questionary validator that only accepts ints between some bounds."""

    class IV(Validator):
        def validate(self, document):
            if len(document.text) == 0:
                raise ValidationError(
                    message="Please enter a value", cursor_position=len(document.text),
                )

            try:
                val = int(document.text)
            except TypeError:
                raise ValidationError(message="Value must be an integer.")

            if val <= minval or val >= maxval:
                raise ValidationError(
                    message=f"Value must be an integer >= {minval} and <= {maxval}"
                )
