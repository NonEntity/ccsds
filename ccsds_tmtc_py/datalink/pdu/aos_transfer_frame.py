import struct
from enum import Enum
import abc

from .abstract_transfer_frame import AbstractTransferFrame, IllegalStateException

class UserDataType(Enum):
    M_PDU = 0  # Multiplexing PDU (contains Space Packets)
    B_PDU = 1  # Bitstream PDU
    VCA = 2    # Virtual Channel Access (contains Encapsulation Packets)
    IDLE = 3   # Idle Data

class AosTransferFrame(AbstractTransferFrame):
    """
    AOS Transfer Frame according to CCSDS 732.0-B-3.
    """
    AOS_PRIMARY_HEADER_LENGTH = 6  # Minimum length of the primary header (excluding FHEC, Insert Zone)
    AOS_PRIMARY_HEADER_FHEC_LENGTH = 2 # Length of the Frame Header Error Control field

    # For M_PDU User Data Type
    AOS_M_PDU_FIRST_HEADER_POINTER_IDLE = 0x07FE # 2046 (b'11111111110')
    AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET = 0x07FF # 2047 (b'11111111111')

    # For B_PDU User Data Type
    AOS_B_PDU_FIRST_HEADER_POINTER_IDLE = 0x3FFE # 16382 (b'11111111111110')
    AOS_B_PDU_FIRST_HEADER_POINTER_ALL_DATA = 0x3FFF # 16383 (b'11111111111111')

    def __init__(self, frame: bytes,
                 frame_header_error_control_present: bool,
                 insert_zone_length: int, # In bytes
                 user_data_type: UserDataType,
                 ocf_present: bool,
                 fecf_present: bool, # From AbstractTransferFrame
                 security_header_length: int = 0,
                 security_trailer_length: int = 0):

        super().__init__(frame, fecf_present) # Stores frame and fecf_present

        self._frame_header_error_control_present = frame_header_error_control_present
        self._insert_zone_length = insert_zone_length
        self._user_data_type = user_data_type
        self._passed_security_header_length = security_header_length
        self._passed_security_trailer_length = security_trailer_length
        self.ocf_present = ocf_present # From AbstractTransferFrame

        min_expected_len = self.AOS_PRIMARY_HEADER_LENGTH
        if self._frame_header_error_control_present:
            min_expected_len += self.AOS_PRIMARY_HEADER_FHEC_LENGTH
        min_expected_len += self._insert_zone_length
        # User data prefix (FHP/BDP) is also expected if type is M_PDU or B_PDU
        if self._user_data_type == UserDataType.M_PDU or self._user_data_type == UserDataType.B_PDU:
            min_expected_len += 2


        if len(frame) < min_expected_len:
            raise ValueError(
                f"Frame too short for AOS primary header, FHEC, insert zone, and user data prefix: "
                f"{len(frame)} bytes, minimum {min_expected_len} bytes required."
            )

        # Parse Primary Header (first 6 bytes)
        _two_octets_1 = struct.unpack(">H", frame[0:2])[0]
        self.transfer_frame_version_number = (_two_octets_1 & 0xC000) >> 14
        if self.transfer_frame_version_number != 1: # AOS version is 1
            raise ValueError(f"Invalid AOS Transfer Frame Version Number: {self.transfer_frame_version_number}, expected 1")

        self.spacecraft_id = (_two_octets_1 & 0x3FC0) >> 6
        self.virtual_channel_id = _two_octets_1 & 0x003F # Also used as GVCID

        # Virtual Channel Frame Count (3 bytes: frame[2], frame[3], frame[4])
        # Handled as big-endian unsigned integer by prepending a null byte
        self.virtual_channel_frame_count = struct.unpack(">I", b'\x00' + frame[2:5])[0]

        signaling_field_byte = frame[5]
        self.replay_flag = (signaling_field_byte & 0x80) != 0
        self.virtual_channel_frame_count_usage_flag = (signaling_field_byte & 0x40) != 0
        self.virtual_channel_frame_count_cycle = signaling_field_byte & 0x0F # Last 4 bits

        if not self.virtual_channel_frame_count_usage_flag and self.virtual_channel_frame_count_cycle != 0:
            raise ValueError("If VC Frame Count Usage Flag is 0, VC Frame Count Cycle must also be 0.")

        # Idle frame determination:
        # 1. If VCID == 63 (All ones for 6 bits)
        # 2. If M_PDU and FHP == IDLE
        # 3. If B_PDU and BDP == IDLE
        self._idle_frame = (self.virtual_channel_id == 0x3F) # VCID 63

        # Calculate offset to the start of the (optional) FHP/BDP field
        self._pointer_field_offset = self.AOS_PRIMARY_HEADER_LENGTH
        if self.frame_header_error_control_present:
            self._pointer_field_offset += self.AOS_PRIMARY_HEADER_FHEC_LENGTH
        self._pointer_field_offset += self.insert_zone_length

        # Initialize M_PDU specific fields
        self.first_header_pointer = self.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET # Default for non-M_PDU or no packet
        self._no_start_packet = True # Default

        # Initialize B_PDU specific fields
        self.bitstream_data_pointer = 0 # Default
        self._bitstream_all_valid = False # Default

        user_data_prefix_len = 0
        if self.user_data_type == UserDataType.M_PDU:
            user_data_prefix_len = 2
            if len(frame) < self._pointer_field_offset + user_data_prefix_len:
                raise ValueError("Frame too short for M_PDU First Header Pointer field.")
            _fhp_val = struct.unpack(">H", frame[self._pointer_field_offset : self._pointer_field_offset + user_data_prefix_len])[0]
            self.first_header_pointer = _fhp_val & 0x07FF # 11 bits for FHP
            self._no_start_packet = (self.first_header_pointer == self.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET)
            if self.first_header_pointer == self.AOS_M_PDU_FIRST_HEADER_POINTER_IDLE:
                self._idle_frame = True
        elif self.user_data_type == UserDataType.B_PDU:
            user_data_prefix_len = 2
            if len(frame) < self._pointer_field_offset + user_data_prefix_len:
                raise ValueError("Frame too short for B_PDU Bitstream Data Pointer field.")
            _bdp_val = struct.unpack(">H", frame[self._pointer_field_offset : self._pointer_field_offset + user_data_prefix_len])[0]
            self.bitstream_data_pointer = _bdp_val & 0x3FFF # 14 bits for BDP
            self._bitstream_all_valid = (self.bitstream_data_pointer == self.AOS_B_PDU_FIRST_HEADER_POINTER_ALL_DATA)
            if self.bitstream_data_pointer == self.AOS_B_PDU_FIRST_HEADER_POINTER_IDLE:
                self._idle_frame = True
        elif self.user_data_type == UserDataType.IDLE:
            self._idle_frame = True


        self.data_field_start = self._pointer_field_offset + user_data_prefix_len + self._passed_security_header_length

        # Calculate data_field_length (from AbstractTransferFrame, needs to be accurate)
        trailer_len = self._passed_security_trailer_length
        if self.ocf_present: # From constructor argument
            trailer_len += 4
        if self.is_fecf_present(): # From AbstractTransferFrame method using superclass's _fecf_present
            trailer_len += 2

        self.data_field_length = len(frame) - self.data_field_start - trailer_len
        if self.data_field_length < 0:
            raise ValueError(f"Calculated negative data field length: {self.data_field_length}. Frame len: {len(frame)}, data_field_start: {self.data_field_start}, trailer_len: {trailer_len}")

        if self.ocf_present: # From constructor argument
            self.ocf_start = len(frame) - (2 if self.is_fecf_present() else 0) - 4 # OCF is before FECF
            if self.ocf_start < 0 or self.ocf_start < self.data_field_start + self.data_field_length - (4 if self.ocf_present else 0): # check overlap
                 raise ValueError(f"OCF overlaps with or precedes data field or security trailer. OCF start: {self.ocf_start}, Data end: {self.data_field_start + self.data_field_length}, Frame len: {len(frame)}")
        else:
            self.ocf_start = -1 # From AbstractTransferFrame

        self.valid = self._check_validity() # From AbstractTransferFrame
        self.valid_header = self._check_fhec() # AOS specific

    def is_idle_frame(self) -> bool:
        return self._idle_frame

    @property
    def frame_header_error_control_present(self) -> bool:
        return self._frame_header_error_control_present

    @property
    def insert_zone_length(self) -> int:
        return self._insert_zone_length

    @property
    def user_data_type(self) -> UserDataType:
        return self._user_data_type

    @property
    def replay_flag(self) -> bool:
        return self._replay_flag

    @property
    def virtual_channel_frame_count_usage_flag(self) -> bool:
        return self._virtual_channel_frame_count_usage_flag

    @property
    def virtual_channel_frame_count_cycle(self) -> int:
        return self._virtual_channel_frame_count_cycle

    # M_PDU specific property
    @property
    def no_start_packet(self) -> bool:
        if self.user_data_type != UserDataType.M_PDU:
            # Or raise IllegalStateException? Java code might return default.
            # Returning current state which defaults to True if not M_PDU.
            return True
        return self._no_start_packet

    # B_PDU specific property
    @property
    def bitstream_all_valid(self) -> bool:
        if self.user_data_type != UserDataType.B_PDU:
            return False # Default if not B_PDU
        return self._bitstream_all_valid

    @property
    def security_header_length(self) -> int:
        return self._passed_security_header_length

    @property
    def security_trailer_length(self) -> int:
        return self._passed_security_trailer_length
    
    @property
    def valid_header(self) -> bool:
        return self._valid_header

    def _check_validity(self) -> bool:
        # Placeholder for actual CRC check if FECF is present.
        # For now, assume the frame is valid if it could be parsed this far.
        # TODO: Implement CRC-16 check if FECF is present.
        return True

    def _check_fhec(self) -> bool:
        # Placeholder for FHEC check.
        # TODO: Implement actual FHEC (typically CRC-16 over primary header).
        if not self.frame_header_error_control_present:
            return True # No FHEC to check
        # Assuming FHEC is correct for now if present
        return True

    def get_insert_zone_copy(self) -> bytes:
        """Returns a copy of the Insert Zone data."""
        if self.insert_zone_length == 0:
            return b''
        
        start_idx = self.AOS_PRIMARY_HEADER_LENGTH
        if self.frame_header_error_control_present:
            start_idx += self.AOS_PRIMARY_HEADER_FHEC_LENGTH
        
        end_idx = start_idx + self.insert_zone_length
        if end_idx > len(self._frame):
            raise ValueError("Insert zone indicated but frame too short.")
        return self._frame[start_idx:end_idx]

    def get_fhec(self) -> int:
        """
        Returns the Frame Header Error Control (FHEC) value.
        This method assumes the FHEC is 2 bytes long.

        Raises:
            IllegalStateException: if FHEC is not present.
        Returns:
            The FHEC value as an integer.
        """
        if not self.frame_header_error_control_present:
            raise IllegalStateException("FHEC not present in this frame")
        
        fhec_start_idx = self.AOS_PRIMARY_HEADER_LENGTH
        return struct.unpack(">H", self._frame[fhec_start_idx : fhec_start_idx + self.AOS_PRIMARY_HEADER_FHEC_LENGTH])[0]

    def get_packet_zone_start_in_frame(self) -> int:
        """
        Returns the absolute start index of the user data part of the Packet Zone within the frame.
        This is the location AFTER the First Header Pointer field for M_PDU.
        """
        if self.user_data_type != UserDataType.M_PDU:
            raise IllegalStateException("Packet Zone is only applicable to M_PDU user data type")
        return self._pointer_field_offset + 2 # Start of user data after FHP

    def get_bitstream_data_zone_start_in_frame(self) -> int:
        """
        Returns the absolute start index of the user data part of the Bitstream Data Zone within the frame.
        This is the location AFTER the Bitstream Data Pointer field for B_PDU.
        """
        if self.user_data_type != UserDataType.B_PDU:
            raise IllegalStateException("Bitstream Data Zone is only applicable to B_PDU user data type")
        return self._pointer_field_offset + 2 # Start of user data after BDP
    
    def get_packet_zone_copy(self) -> bytes:
        """
        Returns a copy of the Packet Zone (FHP + User Data).
        Relevant only for M_PDU user data type.
        """
        if self.user_data_type != UserDataType.M_PDU:
            raise IllegalStateException("Packet Zone is only applicable to M_PDU user data type")
        
        # Packet Zone starts at FHP and includes the data field
        # Data field already excludes security trailer, OCF, FECF
        start_of_fhp = self._pointer_field_offset
        # End of data field relative to frame start: self.data_field_start + self.data_field_length
        # The packet zone includes FHP (2 bytes) and the data field that follows it.
        # self.data_field_start is already pointer_field_offset + 2 (for FHP) + sec_hdr_len
        # So, Packet Zone = FHP + sec_hdr + data_field_proper
        # This means it starts at self._pointer_field_offset and ends at self.data_field_start + self.data_field_length
        
        # As per Java: from FHP start up to (FHP start + length of FHP + length of data field)
        # Data field length here is the "user data for space packet" part.
        # self.data_field_length is this user data part.
        # self.data_field_start points to this user data part.
        # So the zone is FHP (at self._pointer_field_offset) + security_header (if any, between FHP and data_field_start) + data_field
        
        # Let's use the definition from Java: from FHP start up to (FHP start + length of (FHP + data field)).
        # The data field here means the part that get_data_field_copy() returns.
        # The length of FHP is 2.
        # The start of FHP is self._pointer_field_offset.
        # The end of the packet zone would be self.data_field_start + self.data_field_length
        # (since data_field_start is after FHP and sec header).
        # This matches the data from FHP up to the end of the frame's data field.

        end_of_data_field = self.data_field_start + self.data_field_length
        return self._frame[self._pointer_field_offset : end_of_data_field]

    def get_bitstream_data_zone_copy(self) -> bytes:
        """
        Returns a copy of the Bitstream Data Zone (BDP + User Data).
        Relevant only for B_PDU user data type.
        """
        if self.user_data_type != UserDataType.B_PDU:
            raise IllegalStateException("Bitstream Data Zone is only applicable to B_PDU user data type")
        
        # Similar to Packet Zone: BDP (at self._pointer_field_offset) + security_header + data_field
        start_of_bdp = self._pointer_field_offset
        end_of_data_field = self.data_field_start + self.data_field_length
        return self._frame[start_of_bdp : end_of_data_field]

    def get_security_header_copy(self) -> bytes:
        if self.security_header_length == 0:
            return b''
        
        # Security header is after primary header, FHEC, Insert Zone, and FHP/BDP
        start_idx = self._pointer_field_offset
        if self.user_data_type == UserDataType.M_PDU or self.user_data_type == UserDataType.B_PDU:
            start_idx += 2 # For FHP or BDP
        
        end_idx = start_idx + self.security_header_length
        if end_idx > len(self._frame) or start_idx > end_idx:
             raise ValueError("Security header indicated but frame too short or position invalid.")
        return self._frame[start_idx:end_idx]

    def get_security_trailer_copy(self) -> bytes:
        if self.security_trailer_length == 0:
            return b''

        # Security Trailer is located before OCF (if present) and before FECF (if present)
        end_idx = len(self._frame)
        if self.is_fecf_present():
            end_idx -= 2
        if self.ocf_present: # Direct attribute from init
            end_idx -= 4
        
        start_idx = end_idx - self.security_trailer_length
        if start_idx < 0 or start_idx < self.data_field_start + self.data_field_length:
             raise ValueError("Security trailer indicated but frame too short or position invalid.")
        return self._frame[start_idx:end_idx]

    # get_data_field_copy() is inherited from AbstractTransferFrame and uses
    # self.data_field_start (which is after FHP/BDP and sec header) and self.data_field_length.

    def __repr__(self) -> str:
        return (
            f"AosTransferFrame(sc_id={self.spacecraft_id}, vc_id={self.virtual_channel_id}, "
            f"vcfc={self.virtual_channel_frame_count}, user_type={self.user_data_type.name}, "
            f"len={self.get_length()}, replay={self.replay_flag}, idle={self.is_idle_frame()}, "
            f"fhec_pres={self.frame_header_error_control_present}, iz_len={self.insert_zone_length}, "
            f"ocf={self.ocf_present}, fecf={self.is_fecf_present()}, "
            f"data_len={self.get_data_field_length()})"
        )

    def __str__(self) -> str:
        return self.__repr__()


# Example Usage (for testing during development)
if __name__ == '__main__':
    # M_PDU Example
    # Header (6B): TFVN=1(01), SCID=0xAA(0010101010), VCID=0x5(000101) -> 0100101010000101 = 0x4A85
    # VCFC (3B): 0x010203
    # Signaling (1B): Replay=1, VCFCUsage=1, Cycle=0xF -> 11001111 = 0xCF
    aos_header_mpdu = struct.pack(">H3sB", 0x4A85, b'\x01\x02\x03', 0xCF) # 6 bytes

    # FHEC (2B, optional): 0xFFFF
    fhec_bytes = b'\xFF\xFF'

    # Insert Zone (3B, optional): 0xIIJJKK
    insert_zone_bytes = b'\xII\xJJ\xKK'

    # FHP (2B for M_PDU): Ptr=0x123 -> 000000100100011 = 0x0243 (No idle, no no_start)
    fhp_bytes = struct.pack(">H", 0x0243)

    # Security Header (2B, optional): 0xS1S2
    sec_header_bytes = b'\S1\S2'

    # Data (10B): "MPDU_Data!"
    data_bytes_mpdu = b"MPDU_Data!"

    # Security Trailer (1B, optional): 0xT1
    sec_trailer_bytes = b'\T1'

    # OCF (4B, optional): 0x0A0B0C0D
    ocf_bytes = b'\x0A\x0B\x0C\x0D'

    # FECF (2B, optional): 0xEEEE
    fecf_trailer_bytes = b'\xEE\xEE'

    # Full M_PDU Frame
    full_mpdu_frame_data = (aos_header_mpdu + fhec_bytes + insert_zone_bytes + fhp_bytes +
                            sec_header_bytes + data_bytes_mpdu + sec_trailer_bytes +
                            ocf_bytes + fecf_trailer_bytes)
    print(f"Full M_PDU Frame (len {len(full_mpdu_frame_data)}): {full_mpdu_frame_data.hex().upper()}")

    try:
        aos_mpdu = AosTransferFrame(
            frame=full_mpdu_frame_data,
            frame_header_error_control_present=True,
            insert_zone_length=len(insert_zone_bytes),
            user_data_type=UserDataType.M_PDU,
            ocf_present=True,
            fecf_present=True,
            security_header_length=len(sec_header_bytes),
            security_trailer_length=len(sec_trailer_bytes)
        )
        print(f"Parsed M_PDU: {aos_mpdu}")
        print(f"  FHP: {hex(aos_mpdu.first_header_pointer)}")
        print(f"  No Start Packet: {aos_mpdu.no_start_packet}")
        print(f"  Is Idle: {aos_mpdu.is_idle_frame()}")
        print(f"  Insert Zone: {aos_mpdu.get_insert_zone_copy().hex().upper()}")
        print(f"  FHEC: {hex(aos_mpdu.get_fhec())}")
        print(f"  Data Field: {aos_mpdu.get_data_field_copy().decode()} (len {aos_mpdu.get_data_field_length()})")
        print(f"  OCF: {aos_mpdu.get_ocf_copy().hex().upper()}")
        print(f"  FECF: {hex(aos_mpdu.get_fecf())}")
        print(f"  Sec Header: {aos_mpdu.get_security_header_copy().hex().upper()}")
        print(f"  Sec Trailer: {aos_mpdu.get_security_trailer_copy().hex().upper()}")
        print(f"  Packet Zone Start (after FHP): {hex(aos_mpdu.get_packet_zone_start_in_frame())}") # Start of user data
        print(f"  Packet Zone (FHP + Data) Copy: {aos_mpdu.get_packet_zone_copy().hex().upper()}")

    except (ValueError, IllegalStateException) as e:
        print(f"Error parsing M_PDU: {e}")

    # B_PDU Example (minimal, no FHEC, IZ, Security, OCF, FECF)
    # Header (6B): TFVN=1, SCID=0xBB, VCID=0x6 -> 0100101110000110 = 0x4B86
    # VCFC (3B): 0x000001
    # Signaling (1B): Replay=0, VCFCUsage=0, Cycle=0x0 -> 00000000 = 0x00
    aos_header_bpdu = struct.pack(">H3sB", 0x4B86, b'\x00\x00\x01', 0x00)
    # BDP (2B): Ptr=0x100 (points to offset 256 within data zone), not idle, not all_data
    # 0000000100000000 = 0x0100
    bdp_bytes = struct.pack(">H", 0x0100)
    data_bytes_bpdu = b"BitstreamData" * 20 # Make it long enough for pointer
    
    minimal_bpdu_frame_data = aos_header_bpdu + bdp_bytes + data_bytes_bpdu
    print(f"\nMinimal B_PDU Frame (len {len(minimal_bpdu_frame_data)}): {minimal_bpdu_frame_data.hex().upper()}")
    try:
        aos_bpdu = AosTransferFrame(
            frame=minimal_bpdu_frame_data,
            frame_header_error_control_present=False,
            insert_zone_length=0,
            user_data_type=UserDataType.B_PDU,
            ocf_present=False,
            fecf_present=False
        )
        print(f"Parsed B_PDU: {aos_bpdu}")
        print(f"  BDP: {hex(aos_bpdu.bitstream_data_pointer)}")
        print(f"  All Valid: {aos_bpdu.bitstream_all_valid}")
        print(f"  Data Field Len: {aos_bpdu.get_data_field_length()}")
        # print(f"  Data Field: {aos_bpdu.get_data_field_copy().hex().upper()}") # Might be too long
        assert aos_bpdu.get_data_field_length() == len(data_bytes_bpdu)

    except (ValueError, IllegalStateException) as e:
        print(f"Error parsing B_PDU: {e}")

    # Idle Frame (VCID=63)
    # Header (6B): TFVN=1, SCID=0xCC, VCID=63 (0x3F) -> 0100110011111111 = 0x4CFF
    # VCFC (3B): 0x000000
    # Signaling (1B): Replay=0, VCFCUsage=0, Cycle=0x0 -> 00000000 = 0x00
    idle_header = struct.pack(">H3sB", 0x4CFF, b'\x00\x00\x00', 0x00)
    # For VCID=63, user_data_type is typically IDLE, and no FHP/BDP. Data field contains idle pattern.
    idle_data = bytes([0x55] * 20) # Example idle pattern
    idle_frame_data = idle_header + idle_data
    print(f"\nIdle Frame (VCID=63) (len {len(idle_frame_data)}): {idle_frame_data.hex().upper()}")
    try:
        aos_idle = AosTransferFrame(
            frame=idle_frame_data,
            frame_header_error_control_present=False,
            insert_zone_length=0,
            user_data_type=UserDataType.IDLE, # Or M_PDU with FHP_IDLE, or B_PDU with BDP_IDLE
            ocf_present=False,
            fecf_present=False
        )
        print(f"Parsed Idle Frame: {aos_idle}")
        assert aos_idle.is_idle_frame()
        assert aos_idle.user_data_type == UserDataType.IDLE
    except (ValueError, IllegalStateException) as e:
        print(f"Error parsing Idle Frame: {e}")

</tbody>
</table>
