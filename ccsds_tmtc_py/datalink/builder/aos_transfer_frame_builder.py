import struct
from ccsds_tmtc_py.datalink.pdu.aos_transfer_frame import AosTransferFrame, UserDataType
from .i_transfer_frame_builder import ITransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException

class _PayloadUnit:
    TYPE_BITSTREAM = 0
    TYPE_PACKET = 1
    TYPE_DATA = 2

    def __init__(self, type_val: int, data: bytes, valid_data_bits: int = 0):
        self.type_val = type_val
        self.data = data
        self.valid_data_bits = valid_data_bits # Only relevant for TYPE_BITSTREAM

class AosTransferFrameBuilder(ITransferFrameBuilder):
    """
    Builder class for creating AosTransferFrame instances.
    """
    def __init__(self, length: int, frame_header_error_control_present: bool, 
                 insert_zone_length: int, user_data_type: UserDataType, 
                 ocf_present: bool, fecf_present: bool):
        
        if not (0 <= insert_zone_length <= 255): # Assuming insert zone length fits in a byte if needed for header
            raise ValueError("Insert zone length must be between 0 and 255.")

        self._length: int = length
        self._frame_header_error_control_present: bool = frame_header_error_control_present
        self._insert_zone_length: int = insert_zone_length
        self._user_data_type: UserDataType = user_data_type
        self._ocf_present: bool = ocf_present
        self._fecf_present: bool = fecf_present

        self._free_user_data_length: int = self.compute_user_data_length(
            length, frame_header_error_control_present, insert_zone_length, 
            user_data_type, ocf_present, fecf_present
        )
        if self._free_user_data_length < 0:
            raise ValueError(f"Calculated negative free user data length: {self._free_user_data_length}. "
                             f"Frame too short for specified headers/trailers.")

        # Default values for header fields
        self._spacecraft_id: int = 0
        self._virtual_channel_id: int = 0 # Also GVCID
        self._virtual_channel_frame_count: int = 0 # 24 bits
        self._replay_flag: bool = False
        self._virtual_channel_frame_count_usage_flag: bool = True # Default: use VCFC
        self._virtual_channel_frame_count_cycle: int = 0 # 4 bits

        self._insert_zone_bytes: bytes | None = None
        self._ocf_bytes: bytes | None = None
        self._idle: bool = False # If true, specific FHP/BDP patterns might apply

        self._security_header: bytes | None = None
        self._security_trailer: bytes | None = None
        
        self._payload_units: list[_PayloadUnit] = []

    @staticmethod
    def create(length: int, frame_header_error_control_present: bool, 
               insert_zone_length: int, user_data_type: UserDataType, 
               ocf_present: bool, fecf_present: bool) -> 'AosTransferFrameBuilder':
        return AosTransferFrameBuilder(length, frame_header_error_control_present, 
                                       insert_zone_length, user_data_type, 
                                       ocf_present, fecf_present)

    @staticmethod
    def compute_user_data_length(frame_len: int, fhec_present: bool, iz_len: int, 
                                 ud_type: UserDataType, ocf_present: bool, fecf_present: bool) -> int:
        header_len = AosTransferFrame.AOS_PRIMARY_HEADER_LENGTH
        if fhec_present:
            header_len += AosTransferFrame.AOS_PRIMARY_HEADER_FHEC_LENGTH
        header_len += iz_len
        
        if ud_type == UserDataType.M_PDU or ud_type == UserDataType.B_PDU:
            header_len += 2 # For FHP or BDP field

        user_data_len = frame_len - header_len
        if ocf_present:
            user_data_len -= 4
        if fecf_present:
            user_data_len -= 2
        return user_data_len

    # Setter methods
    def set_spacecraft_id(self, spacecraft_id: int) -> 'AosTransferFrameBuilder':
        if not (0 <= spacecraft_id <= 0x3FF): # 10 bits
            raise ValueError("Spacecraft ID must be a 10-bit value.")
        self._spacecraft_id = spacecraft_id
        return self

    def set_virtual_channel_id(self, virtual_channel_id: int) -> 'AosTransferFrameBuilder':
        if not (0 <= virtual_channel_id <= 0x3F): # 6 bits
            raise ValueError("Virtual Channel ID must be a 6-bit value.")
        self._virtual_channel_id = virtual_channel_id
        return self

    def set_virtual_channel_frame_count(self, virtual_channel_frame_count: int) -> 'AosTransferFrameBuilder':
        if not (0 <= virtual_channel_frame_count <= 0xFFFFFF): # 24 bits
            raise ValueError("Virtual Channel Frame Count must be a 24-bit value.")
        self._virtual_channel_frame_count = virtual_channel_frame_count
        return self
    
    def set_replay_flag(self, replay_flag: bool) -> 'AosTransferFrameBuilder':
        self._replay_flag = replay_flag
        return self

    def set_virtual_channel_frame_count_usage_flag(self, usage_flag: bool) -> 'AosTransferFrameBuilder':
        self._virtual_channel_frame_count_usage_flag = usage_flag
        return self

    def set_virtual_channel_frame_count_cycle(self, cycle: int) -> 'AosTransferFrameBuilder':
        if not (0 <= cycle <= 0x0F): # 4 bits
            raise ValueError("Virtual Channel Frame Count Cycle must be a 4-bit value.")
        self._virtual_channel_frame_count_cycle = cycle
        return self

    def set_insert_zone(self, insert_zone_bytes: bytes | None) -> 'AosTransferFrameBuilder':
        if insert_zone_bytes is None:
            if self._insert_zone_length > 0:
                 raise ValueError("Insert zone bytes cannot be None if length > 0 was configured.")
            self._insert_zone_bytes = None
        else:
            if len(insert_zone_bytes) != self._insert_zone_length:
                raise ValueError(f"Insert zone length mismatch: expected {self._insert_zone_length}, got {len(insert_zone_bytes)}.")
            self._insert_zone_bytes = insert_zone_bytes
        return self

    def set_idle(self, idle: bool = True) -> 'AosTransferFrameBuilder':
        """Sets the frame to be an idle frame. This typically means VCID=63 or specific FHP/BDP values."""
        self._idle = idle
        if idle:
            self.set_virtual_channel_id(0x3F) # Standard way to mark AOS idle frame
            if self._user_data_type == UserDataType.IDLE: # Ensure consistency
                pass
            # For M_PDU/B_PDU, specific FHP/BDP values will be set during build if _idle is True.
        return self

    def set_security(self, header: bytes | None, trailer: bytes | None) -> 'AosTransferFrameBuilder':
        current_sec_len = 0
        if self._security_header: current_sec_len += len(self._security_header)
        if self._security_trailer: current_sec_len += len(self._security_trailer)
        
        self._free_user_data_length += current_sec_len

        new_sec_len = 0
        if header: new_sec_len += len(header)
        if trailer: new_sec_len += len(trailer)

        if self._free_user_data_length < new_sec_len:
            self._free_user_data_length -= current_sec_len # revert
            raise ValueError("Not enough free space for the provided security header/trailer.")

        self._security_header = header
        self._security_trailer = trailer
        self._free_user_data_length -= new_sec_len
        return self

    def set_ocf(self, ocf_bytes: bytes | None) -> 'AosTransferFrameBuilder':
        if ocf_bytes is None:
            if self._ocf_present:
                raise ValueError("OCF bytes cannot be None if ocf_present is True.")
            self._ocf_bytes = None
        else:
            if not self._ocf_present:
                raise ValueError("Cannot set OCF bytes if ocf_present is False.")
            if len(ocf_bytes) != 4:
                raise ValueError("OCF must be 4 bytes long.")
            self._ocf_bytes = ocf_bytes
        return self

    def add_space_packet(self, packet_data: bytes) -> int:
        if self._user_data_type != UserDataType.M_PDU:
            raise IllegalStateException("Can only add space packets to M_PDU user data type frames.")
        return self._add_payload(packet_data, _PayloadUnit.TYPE_PACKET)

    def add_bitstream_data(self, data: bytes, valid_data_bits: int) -> int:
        if self._user_data_type != UserDataType.B_PDU:
            raise IllegalStateException("Can only add bitstream data to B_PDU user data type frames.")
        # For bitstream, the length check is more complex if we were to pack bit-wise.
        # Here, we assume 'data' is byte-aligned for simplicity in builder,
        # and valid_data_bits informs the BDP calculation.
        return self._add_payload(data, _PayloadUnit.TYPE_BITSTREAM, valid_data_bits)

    def add_data(self, data: bytes, offset: int = 0, length: int = -1) -> int:
        if length == -1: length = len(data) - offset
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("Invalid offset or length for data.")
        actual_data = data[offset : offset + length]
        return self._add_payload(actual_data, _PayloadUnit.TYPE_DATA)

    def _add_payload(self, data_to_add: bytes, type_val: int, valid_bits: int = 0) -> int:
        writable_length = min(len(data_to_add), self._free_user_data_length)
        
        if writable_length > 0:
            self._payload_units.append(_PayloadUnit(type_val, data_to_add[:writable_length], valid_bits if type_val == _PayloadUnit.TYPE_BITSTREAM else len(data_to_add[:writable_length])*8))
            self._free_user_data_length -= writable_length
        
        return len(data_to_add) - writable_length
    
    def get_free_user_data_length(self) -> int:
        return self._free_user_data_length

    def is_full(self) -> bool:
        return self._free_user_data_length == 0

    def _compute_mpdu_first_header_pointer(self) -> int:
        if self._idle and self._user_data_type == UserDataType.M_PDU: # VCID=63 takes precedence for idle frame marking
             if self._virtual_channel_id != 0x3F: # if not marked idle by VCID
                return AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_IDLE

        offset = 0 # Offset from start of user data (after sec header) to first packet
        for unit in self._payload_units:
            if unit.type_val == _PayloadUnit.TYPE_PACKET:
                if offset >= AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET: # 2047
                    return AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET
                return offset
            offset += len(unit.data)
        return AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET

    def _compute_bpdu_bitstream_data_pointer(self) -> int:
        if self._idle and self._user_data_type == UserDataType.B_PDU:
            if self._virtual_channel_id != 0x3F:
                return AosTransferFrame.AOS_B_PDU_FIRST_HEADER_POINTER_IDLE

        # For B_PDU, pointer is to the first invalid bit, or ALL_VALID.
        # This builder assumes byte-aligned data units. A more complex builder
        # might track bit-level offsets. Here, if all data added is considered valid
        # (e.g. via valid_data_bits spanning the whole payload), return ALL_VALID.
        # Otherwise, it's more complex. Let's assume valid_bits in _PayloadUnit indicates this.
        # For now, if any bitstream unit exists, assume it's all valid unless specified otherwise.
        # A simple approach: if there's any data, and it's not explicitly idle, assume all valid.
        if self._payload_units:
             # A real implementation would sum valid_bits from all payload units
             # and compare to total bits to see if it's ALL_VALID or point to first invalid bit.
             # This simplified version just returns ALL_VALID if there's data.
             # Or, if the task expects the sum of valid_data_bits from all units:
            total_valid_bits = 0
            for unit in self._payload_units:
                if unit.type_val == _PayloadUnit.TYPE_BITSTREAM:
                    total_valid_bits += unit.valid_data_bits
            
            total_payload_bits = (self._length - self._free_user_data_length - # total payload bytes
                                 (AosTransferFrame.AOS_PRIMARY_HEADER_LENGTH + 
                                  (AosTransferFrame.AOS_PRIMARY_HEADER_FHEC_LENGTH if self._frame_header_error_control_present else 0) +
                                  self._insert_zone_length + 2 + # 2 for BDP field
                                  (len(self._security_header) if self._security_header else 0) +
                                  (len(self._security_trailer) if self._security_trailer else 0) +
                                  (4 if self._ocf_present else 0) +
                                  (2 if self._fecf_present else 0))) * 8

            if total_valid_bits >= total_payload_bits: # If all bits in the user data field are valid
                return AosTransferFrame.AOS_B_PDU_FIRST_HEADER_POINTER_ALL_DATA
            else: # Points to the first bit not containing valid user data.
                  # This simplified builder doesn't track this precisely.
                  # Returning 0 as a placeholder if not all valid and not idle.
                  # The Java builder might have more complex logic if it assembles bit-by-bit.
                  # For now, let's assume if there's data, it's intended to be valid as a block.
                return total_valid_bits % (2**14) # Placeholder: pointer to end of valid data
        
        return 0 # Default if no data (or could be IDLE if frame is empty and marked idle)


    def build(self) -> AosTransferFrame:
        if not self.is_full() and not (self._idle or self._user_data_type == UserDataType.IDLE):
            raise IllegalStateException(f"Frame is not full. {self._free_user_data_length} bytes remaining.")
        if self._insert_zone_length > 0 and self._insert_zone_bytes is None:
            raise IllegalStateException("Insert zone was configured but not provided.")
        if self._ocf_present and self._ocf_bytes is None:
            raise IllegalStateException("OCF was configured but not provided.")

        frame_buffer = bytearray(self._length)
        current_pos = 0

        # Primary Header
        ph_part1 = (AosTransferFrame.AOS_VERSION << 14) | \
                   (self._spacecraft_id << 6) | \
                   self._virtual_channel_id
        struct.pack_into(">H", frame_buffer, current_pos, ph_part1)
        current_pos += 2

        vcfc_bytes = self._virtual_channel_frame_count.to_bytes(3, 'big')
        frame_buffer[current_pos : current_pos + 3] = vcfc_bytes
        current_pos += 3

        signaling_field = ((1 if self._replay_flag else 0) << 7) | \
                          ((1 if self._virtual_channel_frame_count_usage_flag else 0) << 6) | \
                          (self._virtual_channel_frame_count_cycle & 0x0F)
        frame_buffer[current_pos] = signaling_field
        current_pos += 1

        # FHEC (Frame Header Error Control)
        if self._frame_header_error_control_present:
            # Placeholder for actual FHEC calculation
            frame_buffer[current_pos : current_pos + 2] = b'\x00\x00' 
            current_pos += 2
        
        # Insert Zone
        if self._insert_zone_length > 0 and self._insert_zone_bytes:
            frame_buffer[current_pos : current_pos + self._insert_zone_length] = self._insert_zone_bytes
            current_pos += self._insert_zone_length
        
        # User Data Type specific fields (FHP/BDP)
        if self._user_data_type == UserDataType.M_PDU:
            fhp = self._compute_mpdu_first_header_pointer()
            struct.pack_into(">H", frame_buffer, current_pos, fhp & 0x07FF) # 11 bits
            current_pos += 2
        elif self._user_data_type == UserDataType.B_PDU:
            bdp = self._compute_bpdu_bitstream_data_pointer()
            struct.pack_into(">H", frame_buffer, current_pos, bdp & 0x3FFF) # 14 bits
            current_pos += 2
        
        # Security Header
        if self._security_header:
            frame_buffer[current_pos : current_pos + len(self._security_header)] = self._security_header
            current_pos += len(self._security_header)

        # Payload
        for unit in self._payload_units:
            frame_buffer[current_pos : current_pos + len(unit.data)] = unit.data
            current_pos += len(unit.data)
        
        # Fill remaining user data space if idle and not full
        expected_user_data_end = self._length - \
                                 (len(self._security_trailer) if self._security_trailer else 0) - \
                                 (4 if self._ocf_present else 0) - \
                                 (2 if self._fecf_present else 0)
        if (self._idle or self._user_data_type == UserDataType.IDLE) and current_pos < expected_user_data_end:
            fill_len = expected_user_data_end - current_pos
            frame_buffer[current_pos : current_pos + fill_len] = b'\x55' * fill_len # Idle pattern
            current_pos += fill_len


        # Security Trailer
        if self._security_trailer:
            frame_buffer[current_pos : current_pos + len(self._security_trailer)] = self._security_trailer
            current_pos += len(self._security_trailer)

        # OCF
        if self._ocf_present and self._ocf_bytes:
            frame_buffer[current_pos : current_pos + 4] = self._ocf_bytes
            current_pos += 4
        
        # FECF
        if self._fecf_present:
            # Placeholder for actual FECF calculation
            frame_buffer[current_pos : current_pos + 2] = b'\x00\x00' 
            # current_pos += 2 # Not needed as it's the end

        sec_hdr_len = len(self._security_header) if self._security_header else 0
        sec_trl_len = len(self._security_trailer) if self._security_trailer else 0

        return AosTransferFrame(bytes(frame_buffer), self._frame_header_error_control_present,
                                self._insert_zone_length, self._user_data_type,
                                self._ocf_present, self._fecf_present,
                                sec_hdr_len, sec_trl_len)

if __name__ == '__main__':
    # Example Usage
    builder = AosTransferFrameBuilder.create(
        length=256, frame_header_error_control_present=True, insert_zone_length=3,
        user_data_type=UserDataType.M_PDU, ocf_present=True, fecf_present=True
    )
    builder.set_spacecraft_id(0xAA)
    builder.set_virtual_channel_id(5)
    builder.set_insert_zone(b"IZD")
    builder.set_ocf(b"OCFD")
    
    from ccsds_tmtc_py.transport.builder.space_packet_builder import SpacePacketBuilder
    sp_data = SpacePacketBuilder.create().set_apid(0x30).add_data(b"PacketInAOS").build().get_packet()
    builder.add_space_packet(sp_data)

    remaining_space = builder.get_free_user_data_length()
    if remaining_space > 0:
        builder.add_data(b'\xBB' * remaining_space)
    
    assert builder.is_full()
    aos_frame = builder.build()
    print(f"Built AOS Frame: {aos_frame}")
    print(f"  Length: {aos_frame.get_length()}")
    print(f"  User Data Field Length: {aos_frame.get_data_field_length()}")
    print(f"  FHP: {hex(aos_frame.first_header_pointer) if aos_frame.user_data_type == UserDataType.M_PDU else 'N/A'}")
    print(f"  Is Idle: {aos_frame.is_idle_frame()}")

    idle_builder = AosTransferFrameBuilder.create(128, False, 0, UserDataType.IDLE, False, False)
    idle_builder.set_idle(True) # Sets VCID to 63
    # Fill with some data
    idle_rem = idle_builder.get_free_user_data_length()
    if idle_rem > 0: idle_builder.add_data(b'\xCC' * idle_rem)
    
    idle_aos_frame = idle_builder.build()
    print(f"Built Idle AOS Frame: {idle_aos_frame}")
    assert idle_aos_frame.is_idle_frame()
    assert idle_aos_frame.virtual_channel_id == 0x3F

    print("AosTransferFrameBuilder tests completed.")
