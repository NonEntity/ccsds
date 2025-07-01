from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class CancelRequest(ICfdpRequest):
    """Request to cancel a transaction."""

    transaction_id: int
