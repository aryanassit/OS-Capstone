"""Custom exceptions so callers can tell bad input from real bugs."""


class ValidationError(ValueError):
    """User/input data is invalid. Safe to show to the user."""


class BridgeError(RuntimeError):
    """A Bash helper script failed or is unavailable."""
