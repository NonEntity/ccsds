import abc

class ITransferFrameBuilder(abc.ABC):
    """
    Abstract base class for Transfer Frame builders.
    """

    @abc.abstractmethod
    def build(self):
        """
        Builds the transfer frame.
        """
        pass

    @abc.abstractmethod
    def get_free_user_data_length(self) -> int:
        """
        Returns the remaining free space for user data in the frame in bytes.
        """
        pass
