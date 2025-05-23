import struct
from enum import Enum
from .i_packet import IPacket

class EncapsulationProtocolIdType(Enum):
    """
    Identifies the protocol of the encapsulated data unit.
    As per Table 6-2 of CCSDS 133.1-B-2 (Encapsulation Packet Proximity Link).
    """
    PROTOCOL_ID_IDLE = 0              # Idle Data
    PROTOCOL_ID_LTP = 1               # CCSDS Data Link Layer LTP
    PROTOCOL_ID_RESERVED_2 = 2        # Reserved by CCSDS
    PROTOCOL_ID_RESERVED_3 = 3        # Reserved by CCSDS
    PROTOCOL_ID_RESERVED_4 = 4        # Reserved by CCSDS
    PROTOCOL_ID_RESERVED_5 = 5        # Reserved by CCSDS
    PROTOCOL_ID_RESERVED_6 = 6        # Reserved by CCSDS
    PROTOCOL_ID_MISSION_SPECIFIC = 7  # Mission Specific Protocol

class EncapsulationPacket(IPacket):
    """
    Encapsulation Packet according to CCSDS 133.1-B-2.
    This packet format is used to encapsulate data units from various protocols
    for transmission over a space link, often within AOS Transfer Frames with
    User Data Type VCA (Virtual Channel Access).
    """
    EP_VERSION = 7  # Packet Version Number (0b111) for Encapsulation Packets
    # Maximum primary header length. Actual length depends on Length of Length field.
    EP_PRIMARY_HEADER_MAX_LENGTH = 8

    def __init__(self, packet_data: bytes, quality_indicator: bool = True):
        """
        Initializes the EncapsulationPacket object.

        Args:
            packet_data: The raw byte string of the encapsulation packet.
            quality_indicator: Indicates the quality of the packet. Not part of the CCSDS standard.

        Raises:
            ValueError: If packet_data is too short for the determined primary header,
                        if the version number is incorrect, or if the total packet length
                        indicated in the header does not match the actual data length.
        """
        if packet_data is None or len(packet_data) < 1: # Need at least 1 byte for the first octet
            raise ValueError("Packet data cannot be None and must be at least 1 byte long.")

        self._packet_data = packet_data
        self._quality_indicator = quality_indicator

        first_octet = self._packet_data[0]
        self._version = (first_octet & 0xE0) >> 5
        if self._version != self.EP_VERSION:
            raise ValueError(f"Invalid Encapsulation Packet Version: {self._version}, expected {self.EP_VERSION}.")

        self._encapsulation_protocol_id = EncapsulationProtocolIdType((first_octet & 0x1C) >> 2)
        
        length_of_length_field_code = first_octet & 0x03  # 00, 01, 10, 11
        header_lengths = [1, 2, 4, 8] # Corresponds to codes 00, 01, 10, 11
        self._primary_header_length = header_lengths[length_of_length_field_code]

        if len(self._packet_data) < self._primary_header_length:
            raise ValueError(
                f"Packet data too short for determined primary header length: "
                f"{len(self._packet_data)} bytes, minimum {self._primary_header_length} bytes required."
            )

        # Initialize optional fields to defaults
        self._encapsulation_protocol_id_extension_present = False
        self._encapsulation_protocol_id_extension = 0
        self._user_defined_field_present = False
        self._user_defined_field = 0
        self._ccsds_defined_field_present = False
        self._ccsds_defined_field = b''

        if self._primary_header_length == 1:
            # Packet contains only the first octet of the Primary Header.
            # This is an Idle Packet. Total Packet Length is implicitly 1.
            self._total_packet_length = 1
        elif self._primary_header_length == 2:
            # Header = 2 octets. Length field is 1 octet (packet_data[1]).
            self._total_packet_length = struct.unpack(">B", self._packet_data[1:2])[0]
        elif self._primary_header_length == 4:
            # Header = 4 octets.
            second_octet = self._packet_data[1]
            self._user_defined_field_present = True
            self._user_defined_field = (second_octet & 0xF0) >> 4
            self._encapsulation_protocol_id_extension_present = True
            self._encapsulation_protocol_id_extension = second_octet & 0x0F
            # Length field is 2 octets (packet_data[2:4]).
            self._total_packet_length = struct.unpack(">H", self._packet_data[2:4])[0]
        else:  # self._primary_header_length == 8
            # Header = 8 octets.
            second_octet = self._packet_data[1]
            self._user_defined_field_present = True
            self._user_defined_field = (second_octet & 0xF0) >> 4
            self._encapsulation_protocol_id_extension_present = True
            self._encapsulation_protocol_id_extension = second_octet & 0x0F
            
            self._ccsds_defined_field_present = True
            self._ccsds_defined_field = self._packet_data[2:4] # CCSDS-Defined Field is 2 octets
            # Length field is 4 octets (packet_data[4:8]).
            self._total_packet_length = struct.unpack(">I", self._packet_data[4:8])[0]

        if len(self._packet_data) != self._total_packet_length:
            raise ValueError(
                f"Actual packet length {len(self._packet_data)} does not match "
                f"total packet length from header {self._total_packet_length}."
            )
            
        self._encapsulated_data_field_length = self._total_packet_length - self._primary_header_length
        if self._encapsulated_data_field_length < 0: # Should not happen if previous checks pass
             raise ValueError("Calculated negative encapsulated data field length.")


    def get_packet(self) -> bytes:
        """Returns the full, raw byte string of the encapsulation packet."""
        return self._packet_data

    def get_length(self) -> int:
        """Returns the total length of the encapsulation packet in bytes."""
        return self._total_packet_length # Use the parsed total length

    def get_version(self) -> int:
        """Returns the version number of the packet (should be 7 for Encapsulation Packets)."""
        return self._version

    @property
    def quality_indicator(self) -> bool:
        """Indicates the quality of the packet (not part of CCSDS standard packet)."""
        return self._quality_indicator

    @property
    def encapsulation_protocol_id(self) -> EncapsulationProtocolIdType:
        """Encapsulation Protocol ID (3 bits)."""
        return self._encapsulation_protocol_id

    @property
    def primary_header_length(self) -> int:
        """Length of the Primary Header in bytes (1, 2, 4, or 8)."""
        return self._primary_header_length

    @property
    def encapsulation_protocol_id_extension_present(self) -> bool:
        """True if the Encapsulation Protocol ID Extension is present."""
        return self._encapsulation_protocol_id_extension_present

    @property
    def encapsulation_protocol_id_extension(self) -> int:
        """Encapsulation Protocol ID Extension (4 bits). Valid if present."""
        return self._encapsulation_protocol_id_extension

    @property
    def user_defined_field_present(self) -> bool:
        """True if the User-Defined Field is present."""
        return self._user_defined_field_present

    @property
    def user_defined_field(self) -> int:
        """User-Defined Field (4 bits). Valid if present."""
        return self._user_defined_field

    @property
    def ccsds_defined_field_present(self) -> bool:
        """True if the CCSDS-Defined Field is present."""
        return self._ccsds_defined_field_present

    @property
    def ccsds_defined_field(self) -> bytes:
        """CCSDS-Defined Field (2 octets). Valid if present."""
        return self._ccsds_defined_field

    @property
    def encapsulated_data_field_length(self) -> int:
        """Length of the Encapsulated Data Field in bytes."""
        return self._encapsulated_data_field_length

    def is_idle(self) -> bool:
        """
        Checks if this is an idle packet.
        Idle packets are identified by Primary Header Length = 1 octet,
        OR Encapsulation Protocol ID = PROTOCOL_ID_IDLE (0).
        """
        return self._primary_header_length == 1 or \
               self.encapsulation_protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_IDLE

    def get_data_field_copy(self) -> bytes:
        """
        Returns a copy of the Encapsulated Data Field of the packet.
        This is the part of the packet after the primary header.
        """
        return self._packet_data[self._primary_header_length:]

    def __repr__(self) -> str:
        return (
            f"EncapsulationPacket(protocol_id={self.encapsulation_protocol_id.name}, "
            f"hdr_len={self.primary_header_length}, total_len={self.get_length()}, "
            f"data_len={self.encapsulated_data_field_length}, idle={self.is_idle()})"
        )

    def __str__(self) -> str:
        return self.__repr__()

# Example Usage
if __name__ == '__main__':
    # Example 1: Idle Packet (Primary Header Length = 1)
    # Version 7 (111), Protocol ID IDLE (000), Length Code 00 (PHL=1) -> 11100000 = 0xE0
    idle_pkt_data_phl1 = bytes([0xE0])
    try:
        ep_idle1 = EncapsulationPacket(idle_pkt_data_phl1)
        print(f"Parsed Idle Packet (PHL=1): {ep_idle1}")
        assert ep_idle1.is_idle()
        assert ep_idle1.primary_header_length == 1
        assert ep_idle1.get_length() == 1
        assert ep_idle1.encapsulated_data_field_length == 0
        assert ep_idle1.encapsulation_protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_IDLE
    except ValueError as e:
        print(f"Error (Idle PHL=1): {e}")

    # Example 2: Short Packet (PHL=2), Protocol LTP, Length 10
    # Version 7 (111), Protocol ID LTP (001), Length Code 01 (PHL=2) -> 11100101 = 0xE5
    # Total Length: 10 (0x0A)
    # Data: 8 bytes "LTP_Data"
    short_pkt_data = bytes([0xE5, 10]) + b"LTP_Data"
    try:
        ep_short = EncapsulationPacket(short_pkt_data)
        print(f"Parsed Short Packet (PHL=2): {ep_short}")
        assert not ep_short.is_idle()
        assert ep_short.primary_header_length == 2
        assert ep_short.get_length() == 10
        assert ep_short.encapsulated_data_field_length == 8
        assert ep_short.encapsulation_protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_LTP
        assert ep_short.get_data_field_copy() == b"LTP_Data"
    except ValueError as e:
        print(f"Error (Short PHL=2): {e}")

    # Example 3: Medium Packet (PHL=4), Protocol Mission Specific, UserDef, ExtID, Length 260
    # Version 7 (111), Protocol Mission (111), Length Code 10 (PHL=4) -> 11111110 = 0xFE
    # UserDef 0xA (1010), ExtID 0x5 (0101) -> 10100101 = 0xA5
    # Total Length: 260 (0x0104)
    # Data: 256 bytes
    medium_pkt_data = bytes([0xFE, 0xA5]) + struct.pack(">H", 260) + (b"M" * 256)
    try:
        ep_medium = EncapsulationPacket(medium_pkt_data)
        print(f"Parsed Medium Packet (PHL=4): {ep_medium}")
        assert ep_medium.primary_header_length == 4
        assert ep_medium.get_length() == 260
        assert ep_medium.encapsulated_data_field_length == 256
        assert ep_medium.encapsulation_protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC
        assert ep_medium.user_defined_field_present
        assert ep_medium.user_defined_field == 0xA
        assert ep_medium.encapsulation_protocol_id_extension_present
        assert ep_medium.encapsulation_protocol_id_extension == 0x5
    except ValueError as e:
        print(f"Error (Medium PHL=4): {e}")

    # Example 4: Long Packet (PHL=8), Protocol Reserved_2, UserDef, ExtID, CCSDSDef, Length 65540
    # Version 7 (111), Protocol Reserved_2 (010), Length Code 11 (PHL=8) -> 11101011 = 0xEB
    # UserDef 0x3 (0011), ExtID 0x7 (0111) -> 00110111 = 0x37
    # CCSDSDef: 0xABCD
    # Total Length: 65540 (0x00010004)
    # Data: 65532 bytes
    long_pkt_data = (bytes([0xEB, 0x37]) + b"\xAB\xCD" + struct.pack(">I", 65540) +
                     (b"L" * (65540 - 8)))
    try:
        ep_long = EncapsulationPacket(long_pkt_data)
        print(f"Parsed Long Packet (PHL=8): {ep_long}")
        assert ep_long.primary_header_length == 8
        assert ep_long.get_length() == 65540
        assert ep_long.encapsulated_data_field_length == (65540 - 8)
        assert ep_long.encapsulation_protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_RESERVED_2
        assert ep_long.user_defined_field_present
        assert ep_long.user_defined_field == 0x3
        assert ep_long.encapsulation_protocol_id_extension_present
        assert ep_long.encapsulation_protocol_id_extension == 0x7
        assert ep_long.ccsds_defined_field_present
        assert ep_long.ccsds_defined_field == b"\xAB\xCD"
    except ValueError as e:
        print(f"Error (Long PHL=8): {e}")

    # Error case: Length mismatch
    try:
        EncapsulationPacket(bytes([0xE5, 20]) + b"LTP_Data") # Expected 20, actual 2 + 8 = 10
    except ValueError as e:
        print(f"Error (Length Mismatch): {e}")

    # Error case: Version mismatch
    try:
        # Version 6 (110) -> 110...
        EncapsulationPacket(bytes([0xD0]))
    except ValueError as e:
        print(f"Error (Version Mismatch): {e}")
