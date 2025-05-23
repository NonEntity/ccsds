import struct
from .i_packet import IPacket
from .common import SequenceFlagType

class SpacePacket(IPacket):
    """
    Space Packet according to CCSDS 133.0-B-1.
    """
    SP_PRIMARY_HEADER_LENGTH = 6
    SP_IDLE_APID_VALUE = 0x07FF  # 2047 (all ones for 11 bits)
    # Max length of CCSDS Packet Data Field is 65536 bytes (as length is uint16)
    MAX_SPACE_PACKET_LENGTH = 65536 + SP_PRIMARY_HEADER_LENGTH
    SP_VERSION = 0 # Version is 000b for Space Packets

    def __init__(self, packet_data: bytes, quality_indicator: bool = True):
        """
        Initializes the SpacePacket object.

        Args:
            packet_data: The raw byte string of the space packet.
            quality_indicator: Indicates the quality of the packet. Typically True for generated packets.
                               Not part of the CCSDS standard packet format itself but often used in ground systems.

        Raises:
            ValueError: If packet_data is too short for the primary header,
                        if the version number is incorrect, or if the packet length
                        indicated in the header does not match the actual data length.
        """
        if len(packet_data) < self.SP_PRIMARY_HEADER_LENGTH:
            raise ValueError(
                f"Packet data too short for Space Packet Primary Header: "
                f"{len(packet_data)} bytes, minimum {self.SP_PRIMARY_HEADER_LENGTH} bytes required."
            )

        self._packet_data = packet_data
        self._quality_indicator = quality_indicator

        # Unpack the primary header (first 6 bytes)
        # Structure:
        # - Packet Version Number (3 bits)
        # - Packet Type (Telemetry/Telecommand) (1 bit)
        # - Secondary Header Flag (1 bit)
        # - APID (Application Process Identifier) (11 bits)
        # - Sequence Flags (2 bits)
        # - Packet Sequence Count or Packet Name (14 bits)
        # - Packet Data Length (16 bits) -> (Total Length of User Data Field - 1)
        ph_part1, ph_part2, ph_part3 = struct.unpack(">HHH", self._packet_data[0:self.SP_PRIMARY_HEADER_LENGTH])

        self._version = (ph_part1 & 0xE000) >> 13
        if self._version != self.SP_VERSION:
            raise ValueError(f"Invalid Space Packet Version: {self._version}, expected {self.SP_VERSION}.")

        self._telemetry_packet_flag = (ph_part1 & 0x1000) == 0  # 0 for TM, 1 for TC
        self._secondary_header_flag = (ph_part1 & 0x0800) != 0
        self._apid = ph_part1 & 0x07FF

        self._sequence_flags_val = (ph_part2 & 0xC000) >> 14
        self._packet_sequence_count = ph_part2 & 0x3FFF  # Or Packet Name

        self._ccsds_packet_data_length = ph_part3  # This is (length of user data field - 1)

        # Validate total packet length against the length specified in the header
        expected_total_len = self._ccsds_packet_data_length + 1 + self.SP_PRIMARY_HEADER_LENGTH
        if len(self._packet_data) != expected_total_len:
            raise ValueError(
                f"Actual packet length {len(self._packet_data)} does not match "
                f"expected length from header {expected_total_len} "
                f"(PrimaryHeader={self.SP_PRIMARY_HEADER_LENGTH} + UserDataLength={self._ccsds_packet_data_length + 1})."
            )
        
        if expected_total_len > self.MAX_SPACE_PACKET_LENGTH:
            # This check is more of a sanity check, as the _ccsds_packet_data_length field (uint16)
            # itself limits the user data part to 65536.
            raise ValueError(
                f"Packet length {expected_total_len} exceeds maximum allowed Space Packet length "
                f"of {self.MAX_SPACE_PACKET_LENGTH} bytes."
            )

    def get_packet(self) -> bytes:
        """Returns the full, raw byte string of the space packet."""
        return self._packet_data

    def get_length(self) -> int:
        """Returns the total length of the space packet in bytes."""
        return len(self._packet_data)

    def get_version(self) -> int:
        """Returns the version number of the packet (should be 0 for Space Packets)."""
        return self._version

    @property
    def quality_indicator(self) -> bool:
        """Indicates the quality of the packet (not part of CCSDS standard packet)."""
        return self._quality_indicator

    @property
    def is_telemetry_packet(self) -> bool:
        """True if this is a Telemetry packet (Packet Type bit = 0), False for Telecommand (Packet Type bit = 1)."""
        return self._telemetry_packet_flag

    @property
    def secondary_header_flag(self) -> bool:
        """True if a Packet Secondary Header is present, False otherwise."""
        return self._secondary_header_flag

    @property
    def apid(self) -> int:
        """Application Process Identifier (11 bits)."""
        return self._apid

    @property
    def sequence_flag(self) -> SequenceFlagType:
        """Sequence Flags (2 bits), indicating segmentation status."""
        return SequenceFlagType(self._sequence_flags_val)

    @property
    def packet_sequence_count(self) -> int:
        """Packet Sequence Count or Packet Name (14 bits)."""
        return self._packet_sequence_count

    @property
    def ccsds_defined_data_length(self) -> int:
        """
        Packet Data Length field from the header (16 bits).
        This value is the length of the User Data Field minus 1.
        """
        return self._ccsds_packet_data_length

    @property
    def user_data_length(self) -> int:
        """
        Actual length of the User Data Field (Packet Data Field) in bytes.
        Calculated as ccsds_defined_data_length + 1.
        """
        return self._ccsds_packet_data_length + 1

    def is_idle(self) -> bool:
        """
        Checks if this is an idle packet.
        Idle packets are identified by APID = 0x7FF (all ones).
        """
        return self.apid == self.SP_IDLE_APID_VALUE

    def get_data_field_copy(self) -> bytes:
        """
        Returns a copy of the User Data Field (Packet Data Field) of the packet.
        This is the part of the packet after the primary header.
        """
        return self._packet_data[self.SP_PRIMARY_HEADER_LENGTH:]

    def __repr__(self) -> str:
        return (
            f"SpacePacket(apid={self.apid}, seq_cnt={self.packet_sequence_count}, "
            f"len={self.get_length()}, user_data_len={self.user_data_length}, "
            f"is_tm={self.is_telemetry_packet}, sh_flag={self.secondary_header_flag}, "
            f"seq_flag={self.sequence_flag.name}, idle={self.is_idle()})"
        )

    def __str__(self) -> str:
        return self.__repr__()

# Example Usage
if __name__ == '__main__':
    # Construct a dummy Space Packet:
    # Version 0 (000), Type TM (0), SH False (0), APID 0x123 (00100100011) -> 0000 0 0 00100100011 = 0x0243
    # Seq UNSEG (11), PSC 0xABCD (0100101010111100) -> 11 0100101010111100 = 0xD4BC
    # Data Length (User Data Length - 1). User Data "TestData" (8 bytes). So, field is 7 (0x0007)
    header_bytes = struct.pack(">HHH", 0x0243, 0xD4BC, 0x0007)
    user_data_bytes = b"TestData"
    packet_bytes = header_bytes + user_data_bytes

    try:
        sp = SpacePacket(packet_bytes)
        print(f"Parsed Space Packet: {sp}")
        print(f"  Version: {sp.get_version()}")
        print(f"  Is Telemetry: {sp.is_telemetry_packet}")
        print(f"  Secondary Header Present: {sp.secondary_header_flag}")
        print(f"  APID: {hex(sp.apid)}")
        print(f"  Sequence Flag: {sp.sequence_flag.name}")
        print(f"  Packet Sequence Count: {hex(sp.packet_sequence_count)}")
        print(f"  CCSDS Data Length Field: {sp.ccsds_defined_data_length}")
        print(f"  User Data Length: {sp.user_data_length}")
        print(f"  Total Packet Length: {sp.get_length()}")
        print(f"  Is Idle: {sp.is_idle()}")
        print(f"  User Data Copy: {sp.get_data_field_copy()}")
        assert sp.get_data_field_copy() == user_data_bytes

        # Idle packet example
        idle_header = struct.pack(">HHH", (0x0000 | sp.SP_IDLE_APID_VALUE), 0xC000, 0xFFFF) # APID=0x7FF, Seq=UNSEG, Len=-1 (actual 0)
        idle_packet_bytes = idle_header + b"" # No user data for this specific idle representation
        
        # Corrected idle packet: user data length 0 means CCSDS length field is 0xFFFF (-1)
        # But the problem statement implies that if APID is IDLE, length can be anything.
        # Standard says "idle packets ... may be of any length up to the maximum packet length"
        # Let's make an idle packet with some data
        idle_header_with_data = struct.pack(">HHH", (0x0000 | sp.SP_IDLE_APID_VALUE), 0xC000, 3) # APID=0x7FF, Seq=UNSEG, UserDataLen=4
        idle_data = b"IDLE"
        idle_packet_with_data_bytes = idle_header_with_data + idle_data
        sp_idle = SpacePacket(idle_packet_with_data_bytes)
        print(f"Parsed Idle Space Packet: {sp_idle}")
        assert sp_idle.is_idle()
        assert sp_idle.user_data_length == 4

        # Error case: too short
        try:
            SpacePacket(b"\x00\x00\x00\x00")
        except ValueError as e:
            print(f"Error (too short): {e}")

        # Error case: wrong version
        try:
            # Version 1 (001) -> 001... -> 0x2... for first octet part
            wrong_version_header = struct.pack(">HHH", (0x2000 | 0x0243), 0xD4BC, 0x0007)
            SpacePacket(wrong_version_header + user_data_bytes)
        except ValueError as e:
            print(f"Error (wrong version): {e}")

        # Error case: length mismatch
        try:
            mismatch_len_header = struct.pack(">HHH", 0x0243, 0xD4BC, 0x000A) # Expect 11 bytes user data
            SpacePacket(mismatch_len_header + user_data_bytes) # Actual 8 bytes user data
        except ValueError as e:
            print(f"Error (length mismatch): {e}")

    except ValueError as e:
        print(f"Error creating SpacePacket: {e}")
