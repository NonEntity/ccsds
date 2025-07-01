from dataclasses import dataclass

from .i_cfdp_indication import ICfdpIndication


@dataclass
class ICfdpTransactionIndication(ICfdpIndication):
    """Base class for indications related to a specific transaction."""

    transaction_id: int
