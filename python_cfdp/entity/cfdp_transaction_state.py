from enum import Enum

class CfdpTransactionState(Enum):
    """Possible states of a CFDP transaction."""
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    ABANDONED = "ABANDONED"
    COMPLETED = "COMPLETED"
