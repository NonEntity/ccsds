from itertools import count

from ..i_transaction_id_generator import ITransactionIdGenerator


class SimpleTransactionIdGenerator(ITransactionIdGenerator):
    """Default transaction ID generator used when none is provided."""

    def __init__(self, start_from: int = 0):
        self._counter = count(start_from)

    def generate_next_transaction_id(self, generating_entity_id: int) -> int:
        return (generating_entity_id << 16) | next(self._counter)
