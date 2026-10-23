"""Expected, actionable failures shared by the CLI and low-level modules."""


class UserFacingError(Exception):
    """An expected failure that should not print a traceback."""


class DataCorruptionError(UserFacingError):
    """Stored data exists but cannot be safely interpreted."""


class ConflictError(UserFacingError):
    """Another writer or a changed input prevents a safe update."""
