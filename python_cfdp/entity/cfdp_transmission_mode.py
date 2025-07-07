from enum import Enum

class CfdpTransmissionMode(Enum):
    """Acknowledgement configuration of a CFDP transaction."""
    CLASS_1 = "Class 1"
    CLASS_1_CLOSURE = "Class 1 with closure"
    CLASS_2 = "Class 2"
    UNKNOWN = "Unknown"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
