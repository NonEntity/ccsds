import abc

class AbstractOcf(abc.ABC):
    """
    Abstract base class for Operational Control Field (OCF) data.
    The OCF is a 4-octet field appended to Transfer Frames.
    """
    def __init__(self, ocf_data: bytes):
        """
        Initializes the AbstractOcf.

        Args:
            ocf_data: The 4-octet OCF data.

        Raises:
            ValueError: If ocf_data is None or not 4 bytes long (actually, task says not empty,
                        but OCF is fixed at 4 bytes. CLCW subclass will enforce 4 bytes).
                        For AbstractOcf, we'll just check not None/empty for now,
                        though specific OCF types will have length checks.
        """
        if ocf_data is None or len(ocf_data) == 0:
            raise ValueError("OCF data cannot be None or empty.")
        
        self._ocf_data: bytes = ocf_data
        # Determine if it's a CLCW based on the first bit (Control Word Type)
        # 0 -> CLCW (Communications Link Control Word)
        # 1 -> Reserved by CCSDS for other OCF types
        self._is_clcw: bool = (self._ocf_data[0] & 0x80) == 0

    @property
    def ocf(self) -> bytes:
        """Returns the raw OCF data."""
        return self._ocf_data

    @property
    def is_clcw(self) -> bool:
        """
        Returns True if this OCF is a Communications Link Control Word (CLCW),
        False otherwise. Determined by the Control Word Type bit (first bit of OCF).
        """
        return self._is_clcw

    def __len__(self) -> int:
        return len(self._ocf_data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(ocf_data=0x{self.ocf.hex().upper()})"

    def __str__(self) -> str:
        return self.__repr__()
