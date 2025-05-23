import abc

class IPacket(abc.ABC):
    """
    Abstract base class for all packet types (e.g., SpacePacket, EncapsulationPacket).
    """

    @abc.abstractmethod
    def get_packet(self) -> bytes:
        """
        Returns the full, raw byte string of the packet.
        """
        pass

    @abc.abstractmethod
    def get_length(self) -> int:
        """
        Returns the total length of the packet in bytes.
        """
        pass

    @abc.abstractmethod
    def get_version(self) -> int:
        """
        Returns the version number of the packet.
        The interpretation of this version depends on the packet type.
        """
        pass
