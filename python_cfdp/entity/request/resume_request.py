from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class ResumeRequest(ICfdpRequest):
    """Request to resume a suspended transaction."""

    transaction_id: int
