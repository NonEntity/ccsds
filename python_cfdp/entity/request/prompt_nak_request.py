from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class PromptNakRequest(ICfdpRequest):
    """Request to send a Prompt NAK."""

    transaction_id: int
