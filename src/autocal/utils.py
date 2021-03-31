"""Simple utilities for use elsewhere in the package."""
import functools
import logging
import numpy as np
import questionary as qs
import sys
from questionary import ValidationError, Validator

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

            if val < minval or val > maxval:
                raise ValidationError(
                    message=f"Value must be an integer >= {minval} and <= {maxval}"
                )

    return IV


def float_validator(minval=-np.inf, maxval=np.inf):
    """Return a questionary validator that only accepts ints between some bounds."""

    class FV(Validator):
        def validate(self, document):
            if len(document.text) == 0:
                raise ValidationError(
                    message="Please enter a value", cursor_position=len(document.text),
                )

            try:
                val = float(document.text)
            except TypeError:
                raise ValidationError(message="Value must be a float.")

            if val < minval or val > maxval:
                raise ValidationError(
                    message=f"Value must be a float >= {minval} and <= {maxval}"
                )

    return FV


def block_on_question(question):
    """Block on affirmation from user, allowing exit."""
    while not qs.confirm(question, default=False).ask():
        if qs.confirm("Would you like to exit then?", default=False).ask():
            sys.exit()
