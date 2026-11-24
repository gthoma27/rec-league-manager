"""Checks for values typed into forms or passed in the URL.

Each function takes the raw text, a label used in messages, and an errors
list. A bad value adds a message to errors and returns None, so a form can
collect every problem at once and show them together.
"""
import re

_WHOLE_NUMBER = re.compile(r'-?[0-9]+')


def parse_int(raw, label, errors, minimum=None, maximum=None, required=True, default=None):
    """A whole number between minimum and maximum. Blank returns default unless required."""
    text = (raw or '').strip()
    if text == '':
        if required:
            errors.append(f'{label} is required.')
        return default
    # The length limit stops absurdly long numbers before int() sees them.
    if len(text) > 12 or not _WHOLE_NUMBER.fullmatch(text):
        errors.append(f'{label} must be a whole number.')
        return None
    value = int(text)
    too_low = minimum is not None and value < minimum
    too_high = maximum is not None and value > maximum
    if too_low or too_high:
        if minimum is not None and maximum is not None:
            errors.append(f'{label} must be between {minimum} and {maximum}.')
        elif minimum is not None:
            errors.append(f'{label} must be at least {minimum}.')
        else:
            errors.append(f'{label} must be at most {maximum}.')
        return None
    return value


def parse_id(raw, label, errors):
    """An ID picked from a drop-down list. label is lower case, like 'home team'."""
    text = (raw or '').strip()
    if text == '':
        article = 'an' if label[0] in 'aeiou' else 'a'
        errors.append(f'Choose {article} {label}.')
        return None
    if len(text) > 12 or not text.isascii() or not text.isdigit() or int(text) < 1:
        errors.append(f'That {label} is not valid.')
        return None
    return int(text)


def parse_text(raw, label, errors, max_length, required=False):
    """Text with surrounding spaces removed, no longer than max_length."""
    text = (raw or '').strip()
    if required and text == '':
        errors.append(f'{label} is required.')
        return None
    if len(text) > max_length:
        errors.append(f'{label} can be at most {max_length} characters.')
        return None
    return text


def parse_choice(raw, label, errors, choices, required=True):
    """One of a fixed set of values. Blank returns '' when not required."""
    text = (raw or '').strip()
    if text == '' and not required:
        return ''
    if text not in choices:
        errors.append(f'{label} must be one of: {", ".join(choices)}.')
        return None
    return text


def parse_checkbox(values, name):
    """1 if the checkbox was ticked, otherwise 0. Unticked boxes aren't sent at all."""
    return 1 if values.get(name) in ('1', 'on', 'yes') else 0
