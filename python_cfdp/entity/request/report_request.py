from dataclasses import dataclass

from .i_cfdp_request import ICfdpRequest


@dataclass
class ReportRequest(ICfdpRequest):
    """Request to obtain a report about a transaction."""

    transaction_id: int
