from enum import Enum


class ActionCode(Enum):
    """Enumeration of filestore action codes."""

    CREATE = "CREATE"
    DELETE = "DELETE"
    RENAME = "RENAME"
    APPEND = "APPEND"
    REPLACE = "REPLACE"
    CREATE_DIRECTORY = "CREATE_DIRECTORY"
    REMOVE_DIRECTORY = "REMOVE_DIRECTORY"
    DENY_FILE = "DENY_FILE"
    DENY_DIRECTORY = "DENY_DIRECTORY"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
