import struct
from ccsds_tmtc_py.datalink.pdu.tc_transfer_frame import TcTransferFrame, FrameType, SequenceFlagType as TcFrameSequenceFlagType
from .i_transfer_frame_builder import ITransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException

class TcTransferFrameBuilder(ITransferFrameBuilder):
    """
    Builder class for creating TcTransferFrame instances.
    """
    def __init__(self, fecf_present: bool):
        self._fecf_present: bool = fecf_present
        
        # Frame properties, to be set by setters
        self._bypass_flag: bool = False
        self._control_command_flag: bool = False # Determines BC_FRAME if True
        self._spacecraft_id: int = 0
        self._virtual_channel_id: int = 0
        self._frame_sequence_number: int = 0 # For AD/BD frames (MAP Channel SDU Sequence Count)

        # Segmentation properties
        self._segmented: bool = False # True if segmentation header is present
        self._map_id: int = 0 # If segmented
        self._sequence_flag: TcFrameSequenceFlagType = TcFrameSequenceFlagType.NO_SEGMENT # If segmented
        
        self._security_header: bytes | None = None
        self._security_trailer: bytes | None = None
        
        self._payload_data: bytes | None = None # User data or control command data

        # Max length is 1024. Header is 5. Optional SegHdr (1), SecHdr, SecTrl, FECF (2).
        self._max_payload_length: int = self.compute_max_user_data_length(fecf_present)
        self._current_payload_length: int = 0 # Actual data written by user
        self._free_user_data_length: int = self._max_payload_length


    @staticmethod
    def create(fecf_present: bool) -> 'TcTransferFrameBuilder':
        return TcTransferFrameBuilder(fecf_present)

    @staticmethod
    def compute_max_user_data_length(fecf_present: bool) -> int:
        """
        Computes the maximum possible user data length considering only primary header and FECF.
        Actual user data length will be less if segmentation or security headers are used.
        """
        min_overhead = TcTransferFrame.TC_PRIMARY_HEADER_LENGTH
        if fecf_present:
            min_overhead += 2
        return TcTransferFrame.MAX_TC_FRAME_LENGTH - min_overhead

    def _update_free_length(self):
        """Recalculates free user data length based on current configuration."""
        overhead = 0
        if self._segmented:
            overhead += 1 # Segmentation header
        if self._security_header:
            overhead += len(self._security_header)
        if self._security_trailer:
            overhead += len(self._security_trailer)
        
        self._free_user_data_length = self._max_payload_length - overhead - self._current_payload_length
        if self._free_user_data_length < 0:
            # This indicates an issue, potentially too much data added before setting headers
            raise ValueError("Negative free user data length calculated. Configuration error or data overflow.")


    # Setters
    def set_bypass_flag(self, bypass_flag: bool) -> 'TcTransferFrameBuilder':
        self._bypass_flag = bypass_flag
        return self

    def set_control_command_flag(self, control_command_flag: bool) -> 'TcTransferFrameBuilder':
        self._control_command_flag = control_command_flag
        # BC frames do not have segmentation or security headers/trailers as per typical usage
        if control_command_flag:
            self._segmented = False 
            self.set_security(None, None) # Clear security for BC frames
        self._update_free_length()
        return self

    def set_spacecraft_id(self, spacecraft_id: int) -> 'TcTransferFrameBuilder':
        if not (0 <= spacecraft_id <= 0x03FF): # 10 bits
            raise ValueError("Spacecraft ID must be a 10-bit value.")
        self._spacecraft_id = spacecraft_id
        return self

    def set_virtual_channel_id(self, virtual_channel_id: int) -> 'TcTransferFrameBuilder':
        if not (0 <= virtual_channel_id <= 0x3F): # 6 bits
            raise ValueError("Virtual Channel ID must be a 6-bit value.")
        self._virtual_channel_id = virtual_channel_id
        return self

    def set_frame_sequence_number(self, frame_sequence_number: int) -> 'TcTransferFrameBuilder':
        # This is the V(R) for BC frames (Set V(R) command), or MAP Channel SDU Sequence Count for AD/BD.
        # The PDU itself doesn't store this directly other than in the data field for Set V(R).
        # For AD/BD, this is not part of the TC frame header directly, but used by MAP channel.
        # The task description implies this sets the VCFC byte.
        if not (0 <= frame_sequence_number <= 0xFF): # 8 bits for VCFC
            raise ValueError("Frame Sequence Number (VCFC) must be an 8-bit value.")
        self._frame_sequence_number = frame_sequence_number # This will be used for VCFC
        return self

    def set_segment(self, map_id: int, sequence_flag: TcFrameSequenceFlagType) -> 'TcTransferFrameBuilder':
        if self._control_command_flag:
            raise IllegalStateException("Segmentation is not applicable to BC (Control Command) frames.")
        if not (0 <= map_id <= 0x3F): # 6 bits
            raise ValueError("MAP ID must be a 6-bit value.")

        was_segmented = self._segmented
        self._segmented = True
        self._map_id = map_id
        self._sequence_flag = sequence_flag
        if not was_segmented: # Only update free length if segmentation state changed to true
            self._update_free_length() 
        return self

    def set_security(self, header: bytes | None, trailer: bytes | None) -> 'TcTransferFrameBuilder':
        if self._control_command_flag:
            # Security typically not used with BC frames, but spec might allow.
            # For this builder, let's disallow for BC to simplify.
            if header or trailer:
                 raise IllegalStateException("Security header/trailer is not supported for BC frames by this builder.")
            self._security_header = None
            self._security_trailer = None
        else:
            self._security_header = header
            self._security_trailer = trailer
        self._update_free_length()
        return self

    def set_unlock_control_command(self) -> 'TcTransferFrameBuilder':
        if not self._control_command_flag:
            raise IllegalStateException("Control Command Flag must be set to true for UNLOCK command.")
        self.clear_data() # Control commands replace other data
        self.add_data(b'\x00')
        return self

    def set_set_vr_control_command(self, fs_number: int) -> 'TcTransferFrameBuilder':
        if not self._control_command_flag:
            raise IllegalStateException("Control Command Flag must be set to true for SET_VR command.")
        if not (0 <= fs_number <= 0xFF):
            raise ValueError("Frame Sequence Number for SET_VR must be an 8-bit value.")
        self.clear_data() # Control commands replace other data
        self.add_data(bytes([0x82, 0x00, fs_number]))
        return self

    def add_data(self, data: bytes, offset: int = 0, length: int = -1) -> int:
        if length == -1:
            length = len(data) - offset
        
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("Invalid offset or length for data.")

        data_to_add = data[offset : offset + length]
        
        # If payload already exists, this replaces it. TC frames carry one PDU or segment.
        if self._payload_data is not None:
            self._current_payload_length = 0 # Reset old length contribution
        
        writable_length = min(len(data_to_add), self._free_user_data_length + self._current_payload_length) # Check against total available after removing old
        
        if writable_length > 0:
            self._payload_data = data_to_add[:writable_length]
            self._current_payload_length = writable_length
        else:
            self._payload_data = None
            self._current_payload_length = 0
            
        self._update_free_length() # Recalculate based on new current_payload_length
        
        return len(data_to_add) - writable_length


    def clear_data(self) -> 'TcTransferFrameBuilder':
        self._payload_data = None
        self._current_payload_length = 0
        self._update_free_length()
        return self

    def get_free_user_data_length(self) -> int:
        return self._free_user_data_length

    def is_full(self) -> bool:
        # Considered "full" if no more free space, or if payload is set (TC frames are not typically "filled" like TM)
        return self._free_user_data_length == 0 or (self._payload_data is not None and self._free_user_data_length >=0)


    def build(self) -> TcTransferFrame:
        if self._payload_data is None and not (self._control_command_flag): # Allow empty payload only if it's not a control command that requires specific data
            # Or if it is a control command that has empty data (not Unlock or SetV(R))
            # This builder expects specific methods for Unlock/SetVR, which set data.
            # Other BC frames might have data or be empty, depending on mission spec.
            # For AD/BD, payload is expected.
            if not self._control_command_flag: # AD/BD frames expect data
                 raise IllegalStateException("Payload data not set for AD/BD frame.")


        frame_len = TcTransferFrame.TC_PRIMARY_HEADER_LENGTH
        if self._segmented: frame_len += 1
        if self._security_header: frame_len += len(self._security_header)
        if self._payload_data: frame_len += len(self._payload_data)
        if self._security_trailer: frame_len += len(self._security_trailer)
        if self._fecf_present: frame_len += 2

        if frame_len > TcTransferFrame.MAX_TC_FRAME_LENGTH:
            raise ValueError(f"Calculated frame length {frame_len} exceeds maximum TC frame length.")

        frame_buffer = bytearray(frame_len)
        current_pos = 0

        # Primary Header
        hdr_part1 = (TcTransferFrame.TC_VERSION << 14) | \
                    ((1 if self._bypass_flag else 0) << 13) | \
                    ((1 if self._control_command_flag else 0) << 12) | \
                    (self._spacecraft_id & 0x03FF)
        
        # Length field is (Total Frame Length - 1)
        hdr_part2 = ((self._virtual_channel_id & 0x3F) << 10) | \
                    ((frame_len - 1) & 0x03FF)
        
        struct.pack_into(">HHB", frame_buffer, current_pos, hdr_part1, hdr_part2, self._frame_sequence_number & 0xFF)
        current_pos += TcTransferFrame.TC_PRIMARY_HEADER_LENGTH

        # Segmentation Header
        if self._segmented:
            seg_hdr_byte = ((self._sequence_flag.value & 0x03) << 6) | (self._map_id & 0x3F)
            frame_buffer[current_pos] = seg_hdr_byte
            current_pos += 1
        
        # Security Header
        if self._security_header:
            frame_buffer[current_pos : current_pos + len(self._security_header)] = self._security_header
            current_pos += len(self._security_header)
        
        # Payload Data
        if self._payload_data:
            frame_buffer[current_pos : current_pos + len(self._payload_data)] = self._payload_data
            current_pos += len(self._payload_data)
            
        # Security Trailer
        if self._security_trailer:
            frame_buffer[current_pos : current_pos + len(self._security_trailer)] = self._security_trailer
            current_pos += len(self._security_trailer)

        # FECF
        if self._fecf_present:
            # Placeholder for actual FECF calculation
            frame_buffer[current_pos : current_pos + 2] = b'\x00\x00'
            # current_pos += 2

        sec_hdr_len = len(self._security_header) if self._security_header else 0
        sec_trl_len = len(self._security_trailer) if self._security_trailer else 0

        # The `segmented_fn` for TcTransferFrame's constructor is to tell the PDU parser
        # whether to expect a segmentation header based on VC config.
        # The builder itself already knows if it *added* one.
        return TcTransferFrame(bytes(frame_buffer), 
                               segmented_fn=lambda vc_id: self._segmented, # PDU uses this to know if seg hdr should be parsed
                               fecf_present=self._fecf_present,
                               security_header_length=sec_hdr_len,
                               security_trailer_length=sec_trl_len)

if __name__ == '__main__':
    # Example AD Frame
    builder_ad = TcTransferFrameBuilder.create(fecf_present=True)
    builder_ad.set_spacecraft_id(0xAB).set_virtual_channel_id(0x5).set_frame_sequence_number(0xCD)
    builder_ad.set_bypass_flag(False).set_control_command_flag(False) # AD Frame
    builder_ad.add_data(b"TestDataPayloadForADFrame")
    
    try:
        tc_frame_ad = builder_ad.build()
        print(f"Built TC AD Frame: {tc_frame_ad}")
        print(f"  Data: {tc_frame_ad.get_data_field_copy().decode()}")
        assert tc_frame_ad.frame_type == FrameType.AD # Determined by flags in PDU
    except (ValueError, IllegalStateException) as e:
        print(f"Error building AD Frame: {e}")

    # Example BC Frame (UNLOCK)
    builder_bc = TcTransferFrameBuilder.create(fecf_present=False)
    builder_bc.set_spacecraft_id(0xAC).set_virtual_channel_id(0x6).set_frame_sequence_number(0xCE)
    builder_bc.set_control_command_flag(True) # BC Frame
    builder_bc.set_unlock_control_command()
    
    try:
        tc_frame_bc = builder_bc.build()
        print(f"Built TC BC UNLOCK Frame: {tc_frame_bc}")
        assert tc_frame_bc.frame_type == FrameType.BC
        assert tc_frame_bc.control_command_type == TcTransferFrame.ControlCommandType.UNLOCK
    except (ValueError, IllegalStateException) as e:
        print(f"Error building BC Frame: {e}")

    # Example BD Frame (Segmented)
    builder_bd = TcTransferFrameBuilder.create(fecf_present=False)
    builder_bd.set_spacecraft_id(0xAD).set_virtual_channel_id(0x7).set_frame_sequence_number(0xCF)
    builder_bd.set_bypass_flag(True) # BD Frame
    builder_bd.set_control_command_flag(False)
    builder_bd.set_segment(map_id=0x0A, sequence_flag=TcFrameSequenceFlagType.CONTINUE)
    builder_bd.add_data(b"SegmentData")
    
    try:
        tc_frame_bd = builder_bd.build()
        print(f"Built TC BD Segmented Frame: {tc_frame_bd}")
        assert tc_frame_bd.frame_type == FrameType.BD
        assert tc_frame_bd.segmented
        assert tc_frame_bd.map_id == 0x0A
    except (ValueError, IllegalStateException) as e:
        print(f"Error building BD Frame: {e}")

    print("TcTransferFrameBuilder tests completed.")
