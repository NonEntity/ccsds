from enum import Enum


class FaultHandlerAction(Enum):
    """Actions to take when a fault condition is detected."""

    NOTICE_OF_CANCELLATION = "NOTICE_OF_CANCELLATION"
    NOTICE_OF_SUSPENSION = "NOTICE_OF_SUSPENSION"
    NO_ACTION = "NO_ACTION"
    ABANDON = "ABANDON"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
