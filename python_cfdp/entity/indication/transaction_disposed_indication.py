from dataclasses import dataclass

from .i_cfdp_transaction_indication import ICfdpTransactionIndication


@dataclass
class TransactionDisposedIndication(ICfdpTransactionIndication):
    """Indication that a transaction has been disposed."""
    pass
