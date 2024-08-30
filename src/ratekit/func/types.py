from functools import wraps
from typing import get_type_hints


def enforce_types_object(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        hints = get_type_hints(func)
        args_to_check = args[1:]
        hints_to_check = list(hints.values())[1:]

        for arg, hint in zip(args_to_check, hints_to_check):
            if not isinstance(arg, hint):
                raise TypeError(f"Argument '{arg}' does not match {hint}")

        return func(*args, **kwargs)
    return wrapper


def enforce_types_functional(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        hints = get_type_hints(func)
        args_to_check = args
        hints_to_check = list(hints.values())

        for arg, hint in zip(args_to_check, hints_to_check):
            if not isinstance(arg, hint):
                raise TypeError(f"Argument '{arg}' does not match {hint}")

        return func(*args, **kwargs)
    return wrapper
