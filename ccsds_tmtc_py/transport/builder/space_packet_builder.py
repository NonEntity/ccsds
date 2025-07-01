import struct
from ccsds_tmtc_py.transport.pdu.space_packet import SpacePacket
from ccsds_tmtc_py.transport.pdu.common import SequenceFlagType

class SpacePacketBuilder:
    """
    Builder class for creating SpacePacket instances.
    """
    def __init__(self, quality_indicator: bool = True):
        """
        Initializes the SpacePacketBuilder.

        Args:
            quality_indicator: The quality indicator for the packets to be built.
        """
        self._quality_indicator: bool = quality_indicator
        self._telemetry_packet_flag: bool = True  # Default to TM
        self._secondary_header_flag: bool = False
        self._apid: int = 0
        self._sequence_flag: SequenceFlagType = SequenceFlagType.UNSEGMENTED
        self._packet_sequence_count: int = 0
        self._payload_units: list[bytes] = []
        # Max user data length for a space packet (payload part)
        self._max_user_data_length: int = 65536 # (2^16) - CCSDS Packet Data Length field is (Length - 1)
        self._current_user_data_length: int = 0

    @staticmethod
    def create(initialiser: SpacePacket = None, copy_data_field: bool = False, quality_indicator: bool = True) -> 'SpacePacketBuilder':
        """
        Static factory method to create a SpacePacketBuilder.
        Can initialize the builder from an existing SpacePacket.

        Args:
            initialiser: An optional SpacePacket to initialize the builder from.
            copy_data_field: If True and initialiser is provided, copies its data field.
            quality_indicator: The quality indicator for the builder.

        Returns:
            A new SpacePacketBuilder instance.
        """
        builder = SpacePacketBuilder(quality_indicator=quality_indicator)
        if initialiser:
            builder.set_apid(initialiser.apid)
            builder.set_packet_sequence_count(initialiser.packet_sequence_count)
            builder.set_secondary_header_flag(initialiser.secondary_header_flag)
            builder.set_sequence_flag(initialiser.sequence_flag)
            if initialiser.is_telemetry_packet:
                builder.set_telemetry_packet()
            else:
                builder.set_telecommand_packet()
            if copy_data_field:
                builder.add_data(initialiser.get_data_field_copy())
        return builder

    def set_quality_indicator(self, quality_indicator: bool) -> 'SpacePacketBuilder':
        self._quality_indicator = quality_indicator
        return self

    def set_telemetry_packet(self) -> 'SpacePacketBuilder':
        self._telemetry_packet_flag = True
        return self

    def set_telecommand_packet(self) -> 'SpacePacketBuilder':
        self._telemetry_packet_flag = False
        return self

    def set_secondary_header_flag(self, secondary_header_flag: bool) -> 'SpacePacketBuilder':
        self._secondary_header_flag = secondary_header_flag
        return self

    def set_apid(self, apid: int) -> 'SpacePacketBuilder':
        if not (0 <= apid <= 0x07FF):
            raise ValueError("APID must be an 11-bit value (0-2047).")
        self._apid = apid
        return self

    def set_idle(self) -> 'SpacePacketBuilder':
        """Sets the APID to the idle value."""
        self.set_apid(SpacePacket.SP_IDLE_APID_VALUE)
        return self

    def set_sequence_flag(self, sequence_flag: SequenceFlagType) -> 'SpacePacketBuilder':
        self._sequence_flag = sequence_flag
        return self

    def set_packet_sequence_count(self, packet_sequence_count: int) -> 'SpacePacketBuilder':
        if not (0 <= packet_sequence_count <= 0x3FFF):
            raise ValueError("Packet Sequence Count must be a 14-bit value (0-16383).")
        self._packet_sequence_count = packet_sequence_count
        return self

    def increment_packet_sequence_count(self) -> 'SpacePacketBuilder':
        self._packet_sequence_count = (self._packet_sequence_count + 1) & 0x3FFF
        return self

    def add_data(self, data: bytes, offset: int = 0, length: int = -1) -> int:
        """
        Adds data to the packet's payload.

        Args:
            data: The byte string containing the data to add.
            offset: The starting offset within the data byte string.
            length: The number of bytes to add from the data. If -1, adds from offset to end.

        Returns:
            The number of bytes from the input data that were NOT written due to space limitations.
        """
        if length == -1:
            length = len(data) - offset
        
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("Invalid offset or length for data.")

        data_to_add = data[offset : offset + length]
        
        writable_length = min(len(data_to_add), self._max_user_data_length - self._current_user_data_length)
        
        if writable_length > 0:
            self._payload_units.append(data_to_add[:writable_length])
            self._current_user_data_length += writable_length
        
        return len(data_to_add) - writable_length

    def get_free_user_data_length(self) -> int:
        """Returns the remaining free space for user data in bytes."""
        return self._max_user_data_length - self._current_user_data_length

    def is_full(self) -> bool:
        """Checks if the user data field is full."""
        return self.get_free_user_data_length() == 0

    def clear_user_data(self) -> 'SpacePacketBuilder':
        """Clears all accumulated user data from the builder."""
        self._payload_units.clear()
        self._current_user_data_length = 0
        return self

    def build(self) -> SpacePacket:
        """
        Builds the SpacePacket.

        Returns:
            A new SpacePacket instance.
        
        Raises:
            ValueError: If packet_data_len_field would be negative (payload too small, should be 0 for empty).
        """
        payload_data = b"".join(self._payload_units)
        
        # Packet Data Length field in header is (Total Length of User Data Field - 1)
        packet_data_len_field = len(payload_data) - 1
        
        # If payload_data is empty, len is 0. packet_data_len_field becomes -1.
        # This is valid and represented as 0xFFFF in an unsigned short.
        if packet_data_len_field < -1 : # Should not happen if _max_user_data_length is respected
             raise ValueError(f"Calculated packet data length field is {packet_data_len_field}, which is invalid.")


        header_part1 = (SpacePacket.SP_VERSION << 13) | \
                       ((0 if self._telemetry_packet_flag else 1) << 12) | \
                       ((1 if self._secondary_header_flag else 0) << 11) | \
                       self._apid
        
        header_part2 = (self._sequence_flag.value << 14) | self._packet_sequence_count
        
        # For struct.pack, H is unsigned short. If packet_data_len_field is -1, it should be 0xFFFF.
        header_part3_unsigned = packet_data_len_field & 0xFFFF # Handles -1 -> 0xFFFF
        
        packet_bytes = struct.pack(">HHH", header_part1, header_part2, header_part3_unsigned) + payload_data
        
        return SpacePacket(packet_bytes, self._quality_indicator)

if __name__ == '__main__':
    # Example Usage
    builder = SpacePacketBuilder()
    builder.set_apid(0x123)
    builder.set_packet_sequence_count(100)
    builder.set_telemetry_packet()
    builder.set_sequence_flag(SequenceFlagType.UNSEGMENTED)
    
    bytes_not_written = builder.add_data(b"TestDataPayloadPart1")
    assert bytes_not_written == 0
    builder.add_data(b"MoreData")
    
    print(f"Free space before build: {builder.get_free_user_data_length()} bytes")
    
    sp = builder.build()
    print(f"Built Space Packet: {sp}")
    print(f"  User Data: {sp.get_data_field_copy()}")
    assert sp.apid == 0x123
    assert sp.packet_sequence_count == 100
    assert sp.user_data_length == len(b"TestDataPayloadPart1MoreData")

    # Test with initialiser
    builder_from_sp = SpacePacketBuilder.create(initialiser=sp, copy_data_field=True)
    sp_copy = builder_from_sp.build()
    print(f"Built copy Space Packet: {sp_copy}")
    assert sp_copy.apid == sp.apid
    assert sp_copy.packet_sequence_count == sp.packet_sequence_count
    assert sp_copy.get_data_field_copy() == sp.get_data_field_copy()

    # Test idle packet
    idle_builder = SpacePacketBuilder().set_idle()
    idle_sp = idle_builder.build()
    print(f"Built Idle Packet: {idle_sp}")
    assert idle_sp.is_idle()
    assert idle_sp.user_data_length == 0
    assert idle_sp.ccsds_defined_data_length == 0xFFFF # -1 for length 0

    # Test max length
    max_data_builder = SpacePacketBuilder().set_apid(0x100)
    max_len_data = b'A' * max_data_builder._max_user_data_length
    not_written = max_data_builder.add_data(max_len_data)
    assert not_written == 0
    assert max_data_builder.is_full()
    not_written_again = max_data_builder.add_data(b"overflow")
    assert not_written_again == len(b"overflow")
    max_sp = max_data_builder.build()
    print(f"Built Max Length Packet: APID={hex(max_sp.apid)}, UserDataLen={max_sp.user_data_length}")
    assert max_sp.user_data_length == max_data_builder._max_user_data_length
    
    builder.clear_user_data()
    assert builder.get_free_user_data_length() == builder._max_user_data_length

    print("SpacePacketBuilder tests completed.")
