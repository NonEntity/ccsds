from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class KeepAliveRequest(ICfdpRequest):
    """Request to send a KeepAlive PDU."""

    transaction_id: int
