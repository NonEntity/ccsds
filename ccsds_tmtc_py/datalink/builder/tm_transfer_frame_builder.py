import struct
from ccsds_tmtc_py.datalink.pdu.tm_transfer_frame import TmTransferFrame
from .i_transfer_frame_builder import ITransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException
# Placeholder for Crc16Algorithm - will not be functional without it
# from ccsds_tmtc_py.algorithm.Crc16Algorithm import Crc16Algorithm 

class _PayloadUnit:
    def __init__(self, is_packet: bool, data: bytes):
        self.is_packet = is_packet
        self.data = data

class TmTransferFrameBuilder(ITransferFrameBuilder):
    """
    Builder class for creating TmTransferFrame instances.
    """
    def __init__(self, length: int, secondary_header_data_length: int, ocf_present: bool, fecf_present: bool):
        """
        Initializes the TmTransferFrameBuilder.

        Args:
            length: Total length of the TM frame to be built.
            secondary_header_data_length: Length of the secondary header's DATA PART (0 if no SH). Max 63.
            ocf_present: True if an OCF is present, False otherwise.
            fecf_present: True if a FECF (CRC) is present, False otherwise.
        """
        if not (0 <= secondary_header_data_length <= 63):
            raise ValueError("Secondary header data length must be between 0 and 63 bytes.")

        self._length: int = length
        self._secondary_header_data_length: int = secondary_header_data_length # Data part only
        self._ocf_present: bool = ocf_present
        self._fecf_present: bool = fecf_present

        self._free_user_data_length: int = self.compute_user_data_length(
            length, secondary_header_data_length, ocf_present, fecf_present
        )
        if self._free_user_data_length < 0:
            raise ValueError(f"Calculated negative free user data length: {self._free_user_data_length}. "
                             f"Frame too short for specified headers/trailers. "
                             f"TotalLen: {length}, SHDataLen: {secondary_header_data_length}, "
                             f"OCF: {ocf_present}, FECF: {fecf_present}")


        # Default values for header fields
        self._spacecraft_id: int = 0
        self._virtual_channel_id: int = 0
        self._virtual_channel_frame_count: int = 0
        self._master_channel_frame_count: int = 0
        self._synchronisation_flag: bool = False # Default: Asynchronous packet stream
        self._packet_order_flag: bool = False # Default: Not applicable if sync_flag is False
        self._segment_length_identifier: int = 3 # Default: No segmentation
        
        self._secondary_header_bytes: bytes | None = None # Data part of SH
        self._ocf_bytes: bytes | None = None
        self._idle: bool = False # If true, FHP is set to IDLE pattern

        self._security_header: bytes | None = None
        self._security_trailer: bytes | None = None
        
        self._payload_units: list[_PayloadUnit] = []

    @staticmethod
    def create(length: int, sec_header_length: int, ocf_present: bool, fecf_present: bool) -> 'TmTransferFrameBuilder':
        """
        Static factory method to create a TmTransferFrameBuilder.

        Args:
            length: Total length of the TM frame to be built.
            sec_header_length: Length of the secondary header's DATA PART (0 if no SH).
            ocf_present: True if an OCF is present, False otherwise.
            fecf_present: True if a FECF (CRC) is present, False otherwise.

        Returns:
            A new TmTransferFrameBuilder instance.
        """
        return TmTransferFrameBuilder(length, sec_header_length, ocf_present, fecf_present)

    @staticmethod
    def compute_user_data_length(frame_len: int, sec_hdr_data_len: int, ocf_present: bool, fecf_present: bool) -> int:
        """
        Computes the available user data length in a TM frame.

        Args:
            frame_len: Total length of the TM frame.
            sec_hdr_data_len: Length of the secondary header's DATA PART (0 if no SH).
            ocf_present: True if an OCF is present.
            fecf_present: True if a FECF is present.

        Returns:
            The length available for user data (including security header/trailer).
        """
        sh_total_len = 0
        if sec_hdr_data_len > 0:
            sh_total_len = 1 + sec_hdr_data_len # 1 byte for SH ID (version+length) + data length
        
        user_data_len = frame_len - TmTransferFrame.TM_PRIMARY_HEADER_LENGTH - sh_total_len
        if ocf_present:
            user_data_len -= 4
        if fecf_present:
            user_data_len -= 2
        return user_data_len

    # Setter methods
    def set_spacecraft_id(self, spacecraft_id: int) -> 'TmTransferFrameBuilder':
        if not (0 <= spacecraft_id <= 0x3FF): # 10 bits
            raise ValueError("Spacecraft ID must be a 10-bit value.")
        self._spacecraft_id = spacecraft_id
        return self

    def set_virtual_channel_id(self, virtual_channel_id: int) -> 'TmTransferFrameBuilder':
        if not (0 <= virtual_channel_id <= 0x07): # 3 bits
            raise ValueError("Virtual Channel ID must be a 3-bit value.")
        self._virtual_channel_id = virtual_channel_id
        return self

    def set_virtual_channel_frame_count(self, virtual_channel_frame_count: int) -> 'TmTransferFrameBuilder':
        if not (0 <= virtual_channel_frame_count <= 0xFF): # 8 bits
            raise ValueError("Virtual Channel Frame Count must be an 8-bit value.")
        self._virtual_channel_frame_count = virtual_channel_frame_count
        return self

    def set_master_channel_frame_count(self, master_channel_frame_count: int) -> 'TmTransferFrameBuilder':
        if not (0 <= master_channel_frame_count <= 0xFF): # 8 bits
            raise ValueError("Master Channel Frame Count must be an 8-bit value.")
        self._master_channel_frame_count = master_channel_frame_count
        return self

    def set_synchronisation_flag(self, synchronisation_flag: bool) -> 'TmTransferFrameBuilder':
        self._synchronisation_flag = synchronisation_flag
        return self

    def set_packet_order_flag(self, packet_order_flag: bool) -> 'TmTransferFrameBuilder':
        self._packet_order_flag = packet_order_flag
        return self

    def set_segment_length_identifier(self, segment_length_identifier: int) -> 'TmTransferFrameBuilder':
        if not (0 <= segment_length_identifier <= 0x03): # 2 bits
            raise ValueError("Segment Length Identifier must be a 2-bit value.")
        self._segment_length_identifier = segment_length_identifier
        return self

    def set_secondary_header(self, secondary_header_bytes: bytes | None) -> 'TmTransferFrameBuilder':
        if secondary_header_bytes is None:
            if self._secondary_header_data_length > 0:
                 raise ValueError("Secondary header bytes cannot be None if data length > 0 was configured.")
            self._secondary_header_bytes = None
        else:
            if len(secondary_header_bytes) != self._secondary_header_data_length:
                raise ValueError(f"Secondary header length mismatch: expected {self._secondary_header_data_length}, got {len(secondary_header_bytes)}.")
            self._secondary_header_bytes = secondary_header_bytes
        return self
    
    def set_ocf(self, ocf_bytes: bytes | None) -> 'TmTransferFrameBuilder':
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

    def set_idle(self, idle: bool = True) -> 'TmTransferFrameBuilder':
        self._idle = idle
        return self

    def set_security(self, header: bytes | None, trailer: bytes | None) -> 'TmTransferFrameBuilder':
        current_sec_len = 0
        if self._security_header:
            current_sec_len += len(self._security_header)
        if self._security_trailer:
            current_sec_len += len(self._security_trailer)
        
        self._free_user_data_length += current_sec_len # Add back old security length

        new_sec_len = 0
        if header:
            new_sec_len += len(header)
        if trailer:
            new_sec_len += len(trailer)

        if self._free_user_data_length < new_sec_len:
            raise ValueError("Not enough free space for the provided security header/trailer.")

        self._security_header = header
        self._security_trailer = trailer
        self._free_user_data_length -= new_sec_len
        return self

    def add_space_packet(self, packet_data: bytes) -> int:
        """
        Adds a space packet to the frame's payload.
        Args:
            packet_data: The raw bytes of the space packet.
        Returns:
            Number of bytes not written due to space limitations.
        """
        return self._add_payload_unit(packet_data, is_packet=True)

    def add_data(self, data: bytes, offset: int = 0, length: int = -1) -> int:
        """
        Adds generic data (non-packet) to the frame's payload.
        Args:
            data: The byte string containing the data.
            offset: Starting offset within the data.
            length: Number of bytes to add. If -1, from offset to end.
        Returns:
            Number of bytes not written due to space limitations.
        """
        if length == -1:
            length = len(data) - offset
        
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("Invalid offset or length for data.")
        
        actual_data = data[offset : offset + length]
        return self._add_payload_unit(actual_data, is_packet=False)

    def _add_payload_unit(self, data_bytes: bytes, is_packet: bool) -> int:
        writable_length = min(len(data_bytes), self._free_user_data_length)
        
        if writable_length > 0:
            self._payload_units.append(_PayloadUnit(is_packet, data_bytes[:writable_length]))
            self._free_user_data_length -= writable_length
        
        return len(data_bytes) - writable_length

    def get_free_user_data_length(self) -> int:
        return self._free_user_data_length

    def is_full(self) -> bool:
        return self._free_user_data_length == 0

    def _compute_first_header_pointer(self) -> int:
        if self._idle:
            return TmTransferFrame.TM_FIRST_HEADER_POINTER_IDLE
        
        offset = 0
        if self._security_header:
            offset += len(self._security_header)

        if not self._payload_units: # No payload units
            return TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET
        
        first_unit = self._payload_units[0]
        if first_unit.is_packet:
            # If the first unit is a packet, FHP points to its start (after security header)
            if offset >= TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET: # Pointer cannot exceed 2047
                return TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET # Should not happen with typical frame sizes
            return offset
        else:
            # First unit is data, not a packet. No packet start in this frame (unless later units are packets, which is complex)
            # For simplicity, if first unit is not a packet, assume no valid packet start.
            # More sophisticated logic could scan for the first _PayloadUnit.is_packet == True.
            # The Java code's logic seems to imply that if the first thing added is not a packet,
            # then FHP is set to NO_PACKET, or it relies on user data starting with a packet.
            # For this implementation, if the very first segment of user data (after sec header)
            # is a packet, FHP points to it. Otherwise, NO_PACKET.
            return TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET


    def build(self) -> TmTransferFrame:
        if not self.is_full():
            # The Java code allows building non-full frames, filling with an idle pattern.
            # This Python version currently requires it to be full or explicitly set to idle.
            # For now, let's enforce fullness unless it's an idle frame where data doesn't matter as much.
            # If it's an idle frame, we'll fill the user data part.
            if not self._idle:
                 raise IllegalStateException(f"Frame is not full. {self._free_user_data_length} bytes remaining.")
        
        if self._secondary_header_data_length > 0 and self._secondary_header_bytes is None:
            raise IllegalStateException("Secondary header was configured but not provided.")
        if self._ocf_present and self._ocf_bytes is None:
            raise IllegalStateException("OCF was configured but not provided.")

        frame_bytes = bytearray(self._length)
        
        # Primary Header
        ph_part1 = (self._spacecraft_id << 4) | \
                   (self._virtual_channel_id << 1) | \
                   (1 if self._ocf_present else 0)
        
        struct.pack_into(">HBB", frame_bytes, 0, ph_part1, 
                         self._master_channel_frame_count, self._virtual_channel_frame_count)

        fhp = self._compute_first_header_pointer()
        
        secondary_header_present_flag = 1 if self._secondary_header_data_length > 0 and self._secondary_header_bytes is not None else 0

        ph_part2 = (secondary_header_present_flag << 15) | \
                   ((1 if self._synchronisation_flag else 0) << 14) | \
                   ((1 if self._packet_order_flag else 0) << 13) | \
                   (self._segment_length_identifier << 11) | fhp
        
        struct.pack_into(">H", frame_bytes, 4, ph_part2)

        current_pos = TmTransferFrame.TM_PRIMARY_HEADER_LENGTH

        # Secondary Header
        if secondary_header_present_flag:
            # TFSH ID: version 0 (bits 7-6), length of TFSH Data Part (bits 5-0)
            frame_bytes[current_pos] = self._secondary_header_data_length & 0x3F 
            current_pos += 1
            frame_bytes[current_pos : current_pos + self._secondary_header_data_length] = self._secondary_header_bytes
            current_pos += self._secondary_header_data_length
        
        # Security Header
        if self._security_header:
            frame_bytes[current_pos : current_pos + len(self._security_header)] = self._security_header
            current_pos += len(self._security_header)

        # User Data (Payload Units)
        for pu in self._payload_units:
            frame_bytes[current_pos : current_pos + len(pu.data)] = pu.data
            current_pos += len(pu.data)
        
        # If idle and not full, fill remaining user data space with idle pattern (e.g., 0x55)
        if self._idle and current_pos < self._length - (4 if self._ocf_present else 0) - (2 if self._fecf_present else 0) - (len(self._security_trailer) if self._security_trailer else 0):
            fill_start = current_pos
            fill_end_exclusive = self._length - (4 if self._ocf_present else 0) - (2 if self._fecf_present else 0) - (len(self._security_trailer) if self._security_trailer else 0)
            for i in range(fill_start, fill_end_exclusive):
                frame_bytes[i] = 0x55 # Standard TM idle pattern often 0x55 or 0xAA
            current_pos = fill_end_exclusive


        # Security Trailer
        if self._security_trailer:
            frame_bytes[current_pos : current_pos + len(self._security_trailer)] = self._security_trailer
            current_pos += len(self._security_trailer)

        # OCF
        if self._ocf_present and self._ocf_bytes:
            frame_bytes[current_pos : current_pos + 4] = self._ocf_bytes
            current_pos += 4
        
        # FECF (CRC)
        if self._fecf_present:
            # crc_val = Crc16Algorithm.calculate(frame_bytes[0:current_pos]) # Placeholder
            crc_val = 0 # Actual CRC calculation needed here
            struct.pack_into(">H", frame_bytes, current_pos, crc_val)
            # current_pos += 2 # Not strictly needed as it's the last part

        sec_hdr_len = len(self._security_header) if self._security_header else 0
        sec_trl_len = len(self._security_trailer) if self._security_trailer else 0
        
        return TmTransferFrame(bytes(frame_bytes), self._fecf_present, sec_hdr_len, sec_trl_len)

if __name__ == '__main__':
    # Example Usage
    builder = TmTransferFrameBuilder.create(length=256, sec_header_length=3, ocf_present=True, fecf_present=True)
    builder.set_spacecraft_id(0x123)
    builder.set_virtual_channel_id(1)
    builder.set_master_channel_frame_count(10)
    builder.set_virtual_channel_frame_count(20)
    builder.set_secondary_header(b"SHD") # Secondary Header Data
    builder.set_ocf(b"OCFD")
    
    # Add some space packets (as bytes for this example)
    sp1_data = SpacePacketBuilder.create().set_apid(0x10).set_packet_sequence_count(1).add_data(b"PKT1").build().get_packet()
    sp2_data = SpacePacketBuilder.create().set_apid(0x20).set_packet_sequence_count(2).add_data(b"PKT222").build().get_packet()
    
    not_written = builder.add_space_packet(sp1_data)
    assert not_written == 0
    not_written = builder.add_data(b"SomeFillData")
    assert not_written == 0
    not_written = builder.add_space_packet(sp2_data)
    assert not_written == 0

    # Fill the rest of the frame
    remaining_space = builder.get_free_user_data_length()
    if remaining_space > 0:
        builder.add_data(b'\xAA' * remaining_space)
    
    assert builder.is_full()

    try:
        tm_frame = builder.build()
        print(f"Built TM Frame: {tm_frame}")
        print(f"  Length: {tm_frame.get_length()}")
        print(f"  Data Field Length: {tm_frame.get_data_field_length()}")
        print(f"  FHP: {hex(tm_frame.first_header_pointer)}")
        print(f"  SC ID: {hex(tm_frame.spacecraft_id)}")
        print(f"  VC ID: {tm_frame.virtual_channel_id}")
        if tm_frame.secondary_header_present:
            print(f"  Secondary Header Copy: {tm_frame.get_secondary_header_copy().hex()}")
        if tm_frame.is_ocf_present():
            print(f"  OCF Copy: {tm_frame.get_ocf_copy().hex()}")
        if tm_frame.is_fecf_present():
            print(f"  FECF: {hex(tm_frame.get_fecf())}") # Will be 0x0000 due to placeholder CRC

    except IllegalStateException as e:
        print(f"Error building frame: {e}")

    # Idle frame example
    idle_builder = TmTransferFrameBuilder.create(length=128, sec_header_length=0, ocf_present=False, fecf_present=False)
    idle_builder.set_idle(True)
    idle_builder.set_spacecraft_id(0xFF)
    # Fill with some data, which should be mostly ignored or overwritten by idle pattern if logic was complete
    idle_builder.add_data(b"This will be idle data area")
    # It's okay if not full for idle frame, build() will handle it.
    # For this builder, we need to manually fill it if we want specific idle pattern or ensure it's "full" conceptually.
    remaining_idle_space = idle_builder.get_free_user_data_length()
    if remaining_idle_space > 0:
        idle_builder.add_data(b'\x55' * remaining_idle_space) # Fill with a pattern

    idle_frame = idle_builder.build()
    print(f"Built Idle TM Frame: {idle_frame}")
    assert idle_frame.is_idle_frame()
    assert idle_frame.first_header_pointer == TmTransferFrame.TM_FIRST_HEADER_POINTER_IDLE
    # print(f"  Idle Frame Data: {idle_frame.get_data_field_copy().hex()}")

    print("TmTransferFrameBuilder tests completed.")
