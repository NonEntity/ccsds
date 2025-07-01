from abc import ABC, abstractmethod


class ITransactionIdGenerator(ABC):
    """Strategy interface for transaction ID generation."""

    @abstractmethod
    def generate_next_transaction_id(self, generating_entity_id: int) -> int:
        """Return a new transaction identifier."""
        raise NotImplementedError
