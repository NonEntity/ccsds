import abc

class IllegalStateException(Exception):
    """
    Indicates that a method has been invoked at an illegal or
    inappropriate time.
    """
    pass

class AbstractTransferFrame(abc.ABC):
    """
    Abstract base class for CCSDS Transfer Frames.
    Based on eu.dariolucia.ccsds.tmtc.datalink.pdu.AbstractTransferFrame.
    """

    def __init__(self, frame: bytes, fecf_present: bool):
        self._frame: bytes = frame
        self._fecf_present: bool = fecf_present

        # Attributes to be set by subclasses, defaults provided
        self.transfer_frame_version_number: int = 0 # Default, should be overridden if applicable
        self.spacecraft_id: int = 0 # Default, should be overridden
        self.virtual_channel_id: int = 0 # Default, should be overridden
        self.virtual_channel_frame_count: int = 0 # Default, should be overridden

        self.data_field_start: int = 0 # Start index of the data field
        self.data_field_length: int = 0 # Length of the data field

        self.ocf_start: int = -1 # Start index of OCF, -1 if not present
        self.ocf_present: bool = False # OCF presence flag

        self.valid: bool = False # Frame validity (e.g., CRC check)

    def get_frame(self) -> bytes:
        """Returns a direct reference to the underlying frame data."""
        return self._frame

    def get_frame_copy(self) -> bytes:
        """Returns a copy of the underlying frame data."""
        return self._frame[:]

    def get_length(self) -> int:
        """Returns the total length of the transfer frame in bytes."""
        return len(self._frame)

    def is_fecf_present(self) -> bool:
        """Returns true if the Frame Error Control Field (FECF) is present, false otherwise."""
        return self._fecf_present

    def get_fecf(self) -> int:
        """
        Returns the Frame Error Control Field (FECF) value.
        This method assumes the FECF is 2 bytes long.

        Raises:
            IllegalStateException: if FECF is not present.
        Returns:
            The FECF value as an integer.
        """
        if not self._fecf_present:
            raise IllegalStateException("FECF not present in this frame")
        # The FECF is the last 2 bytes of the frame
        import struct
        return struct.unpack(">H", self._frame[self.get_length() - 2 : self.get_length()])[0]

    def is_ocf_present(self) -> bool:
        """Returns true if the Operational Control Field (OCF) is present, false otherwise."""
        return self.ocf_present # This is set by subclass

    def get_ocf_copy(self) -> bytes:
        """
        Returns a copy of the Operational Control Field (OCF).
        This method assumes the OCF is 4 bytes long.

        Raises:
            IllegalStateException: if OCF is not present.
        Returns:
            A copy of the OCF as bytes.
        """
        if not self.ocf_present or self.ocf_start == -1:
            raise IllegalStateException("OCF not present in this frame")
        # Ensure ocf_start is valid and within frame boundaries
        if not (0 <= self.ocf_start < len(self._frame) and self.ocf_start + 4 <= len(self._frame)):
            raise IllegalStateException(f"OCF start index {self.ocf_start} or length is out of bounds for frame length {len(self._frame)}")
        return self._frame[self.ocf_start : self.ocf_start + 4]

    def get_data_field_copy(self) -> bytes:
        """
        Returns a copy of the Transfer Frame Data Field.
        This field contains either Space Packets, Encapsulation Packets,
        TC Space Data Link Protocol PDUs or Idle Data.
        """
        if self.data_field_start < 0 or self.data_field_length < 0 or \
           self.data_field_start + self.data_field_length > len(self._frame):
            # This case might indicate an internal logic error or a corrupted frame structure
            return b''
        return self._frame[self.data_field_start : self.data_field_start + self.data_field_length]

    def get_data_field_length(self) -> int:
        """
        Returns the length of the Transfer Frame Data Field in bytes.
        """
        return self.data_field_length

    def is_valid(self) -> bool:
        """
        Returns whether the frame is valid or not. This is typically
        checked by verifying the FECF if present, or other means.
        Subclasses should set the 'valid' attribute.
        """
        return self.valid

    @abc.abstractmethod
    def is_idle_frame(self) -> bool:
        """
        Indicates whether this frame is an idle frame.
        Idle frames fill the channel when no user data is available.
        """
        pass
