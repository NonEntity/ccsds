from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class SuspendRequest(ICfdpRequest):
    """Request to suspend a running transaction."""

    transaction_id: int
