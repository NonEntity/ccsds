import struct
import abc

from .abstract_transfer_frame import AbstractTransferFrame, IllegalStateException

class TmTransferFrame(AbstractTransferFrame):
    """
    TM Transfer Frame according to CCSDS 132.0-B-2.
    """
    TM_PRIMARY_HEADER_LENGTH = 6
    TM_FIRST_HEADER_POINTER_NO_PACKET = 0x07FF # b'11111111111' (2047)
    TM_FIRST_HEADER_POINTER_IDLE = 0x07FE # b'11111111110' (2046)

    def __init__(self, frame: bytes, fecf_present: bool, security_header_length: int = 0, security_trailer_length: int = 0):
        super().__init__(frame, fecf_present)

        self._security_header_length: int = security_header_length
        self._security_trailer_length: int = security_trailer_length

        if len(frame) < self.TM_PRIMARY_HEADER_LENGTH:
            raise ValueError(
                f"Frame too short for TM primary header: {len(frame)} bytes, "
                f"minimum {self.TM_PRIMARY_HEADER_LENGTH} bytes required."
            )

        # Parse Primary Header (first 6 bytes)
        # Structure:
        # - Transfer Frame Version Number (2 bits)
        # - Spacecraft ID (10 bits)
        # - Virtual Channel ID (3 bits)
        # - OCF Present Flag (1 bit)
        # - Master Channel Frame Count (8 bits)
        # - Virtual Channel Frame Count (8 bits)
        # - Transfer Frame Secondary Header Present Flag (1 bit)
        # - Synchronisation Flag (1 bit)
        # - Packet Order Flag (1 bit)
        # - Segment Length Identifier (2 bits)
        # - First Header Pointer (11 bits)
        _two_octets_1, self._master_channel_frame_count_byte, self._virtual_channel_frame_count_byte, _two_octets_2 = struct.unpack(
            ">HBBH", frame[:self.TM_PRIMARY_HEADER_LENGTH]
        )

        self.transfer_frame_version_number = (_two_octets_1 & 0xC000) >> 14
        if self.transfer_frame_version_number != 0: # TM version is 0
            raise ValueError(f"Invalid TM Transfer Frame Version Number: {self.transfer_frame_version_number}, expected 0")

        self.spacecraft_id = (_two_octets_1 & 0x3FF0) >> 4
        self.virtual_channel_id = (_two_octets_1 & 0x000E) >> 1
        self.ocf_present = (_two_octets_1 & 0x0001) != 0

        # Already assigned via property setters below
        # self.master_channel_frame_count = self._master_channel_frame_count_byte
        # self.virtual_channel_frame_count = self._virtual_channel_frame_count_byte

        self._secondary_header_present = (_two_octets_2 & 0x8000) != 0
        self._synchronisation_flag = (_two_octets_2 & 0x4000) != 0
        self._packet_order_flag = (_two_octets_2 & 0x2000) != 0
        self._segment_length_identifier = (_two_octets_2 & 0x1800) >> 11
        self._first_header_pointer = _two_octets_2 & 0x07FF

        if not self.synchronisation_flag and self.packet_order_flag:
            raise ValueError("Packet Order Flag must be 0 if Synchronisation Flag is 0")
        if not self.synchronisation_flag and self.segment_length_identifier != 3: # 3 means "No Segmentation"
            raise ValueError("Segment Length Identifier must be 3 (No Segmentation) if Synchronisation Flag is 0")

        self._no_start_packet = self.first_header_pointer == self.TM_FIRST_HEADER_POINTER_NO_PACKET
        self._idle_frame = self.first_header_pointer == self.TM_FIRST_HEADER_POINTER_IDLE

        self._secondary_header_version_number: int = 0
        self._secondary_header_data_length: int = 0 # Java secondaryHeaderLength is just data part

        self.data_field_start = self.TM_PRIMARY_HEADER_LENGTH

        if self.secondary_header_present:
            if len(frame) < self.TM_PRIMARY_HEADER_LENGTH + 1:
                raise ValueError("Frame too short for Secondary Header ID byte")
            tfsh_id_byte = frame[self.TM_PRIMARY_HEADER_LENGTH]
            self._secondary_header_version_number = (tfsh_id_byte & 0xC0) >> 6
            self._secondary_header_data_length = tfsh_id_byte & 0x3F # Length of TFSH Data part
            if len(frame) < self.TM_PRIMARY_HEADER_LENGTH + 1 + self.secondary_header_data_length:
                 raise ValueError(f"Frame too short for Secondary Header data: {len(frame)} bytes, "
                                  f"expected {self.TM_PRIMARY_HEADER_LENGTH + 1 + self.secondary_header_data_length}")
            self.data_field_start += (1 + self.secondary_header_data_length) # 1 byte for ID + data length

        self.data_field_start += self._security_header_length

        # Calculate data_field_length
        frame_len = len(frame)
        end_offset = 0
        if fecf_present:
            end_offset += 2
        if self.ocf_present:
            end_offset += 4
        end_offset += self._security_trailer_length

        self.data_field_length = frame_len - self.data_field_start - end_offset
        if self.data_field_length < 0:
            raise ValueError(f"Calculated negative data field length: {self.data_field_length}. Frame len: {frame_len}, data_field_start: {self.data_field_start}, end_offset: {end_offset}")


        if self.ocf_present:
            self.ocf_start = frame_len - (2 if fecf_present else 0) - 4
            if self.ocf_start < self.data_field_start + self.data_field_length: # OCF should be after data field
                 raise ValueError(f"OCF overlaps with or precedes data field or security trailer. OCF start: {self.ocf_start}, Data end: {self.data_field_start + self.data_field_length}")
        else:
            self.ocf_start = -1

        self.valid = self._check_validity()

    @property
    def master_channel_frame_count(self) -> int:
        return self._master_channel_frame_count_byte

    @property
    def virtual_channel_frame_count(self) -> int: # Overrides from AbstractTransferFrame
        return self._virtual_channel_frame_count_byte

    @property
    def secondary_header_present(self) -> bool:
        return self._secondary_header_present

    @property
    def synchronisation_flag(self) -> bool:
        return self._synchronisation_flag

    @property
    def packet_order_flag(self) -> bool:
        return self._packet_order_flag

    @property
    def segment_length_identifier(self) -> int:
        return self._segment_length_identifier

    @property
    def first_header_pointer(self) -> int:
        return self._first_header_pointer

    @property
    def no_start_packet(self) -> bool:
        return self._no_start_packet

    @property
    def secondary_header_version_number(self) -> int:
        return self._secondary_header_version_number

    @property
    def secondary_header_data_length(self) -> int: # Java: secondaryHeaderLength
        return self._secondary_header_data_length

    @property
    def security_header_length(self) -> int:
        return self._security_header_length

    @property
    def security_trailer_length(self) -> int:
        return self._security_trailer_length

    def is_idle_frame(self) -> bool:
        """
        Indicates whether this frame is an idle frame.
        Idle frames fill the channel when no user data is available.
        The First Header Pointer field is set to 0b11111111110 (2046) for idle frames.
        """
        return self._idle_frame

    def get_secondary_header_copy(self) -> bytes:
        """
        Returns a copy of the Transfer Frame Secondary Header (TFSH) data part.
        The TFSH consists of an ID byte (version + length) and the data part itself.
        This method returns only the data part.

        Raises:
            IllegalStateException: if TFSH is not present.
        Returns:
            A copy of the TFSH data as bytes.
        """
        if not self.secondary_header_present:
            raise IllegalStateException("Secondary Header not present in this frame")
        # The secondary header data starts after the TM primary header and the 1-byte TFSH ID
        start_idx = self.TM_PRIMARY_HEADER_LENGTH + 1
        end_idx = start_idx + self.secondary_header_data_length
        return self._frame[start_idx:end_idx]

    def get_security_header_copy(self) -> bytes:
        """
        Returns a copy of the Security Header.

        Returns:
            A copy of the Security Header as bytes, or b'' if not present.
        """
        if self.security_header_length == 0:
            return b''
        
        start_idx = self.TM_PRIMARY_HEADER_LENGTH
        if self.secondary_header_present:
            start_idx += (1 + self.secondary_header_data_length)
        
        end_idx = start_idx + self.security_header_length
        return self._frame[start_idx:end_idx]

    def get_security_trailer_copy(self) -> bytes:
        """
        Returns a copy of the Security Trailer.

        Returns:
            A copy of the Security Trailer as bytes, or b'' if not present.
        """
        if self.security_trailer_length == 0:
            return b''

        # Security Trailer is located before OCF (if present) and before FECF (if present)
        end_idx = len(self._frame)
        if self.is_fecf_present():
            end_idx -= 2
        if self.is_ocf_present(): # uses self.ocf_present which is parsed from header
            end_idx -= 4
        
        start_idx = end_idx - self.security_trailer_length
        return self._frame[start_idx:end_idx]

    def _check_validity(self) -> bool:
        # Placeholder for actual CRC check or other validity checks.
        # For now, assume the frame is valid if it could be parsed this far.
        # TODO: Implement CRC-16 check if FECF is present.
        return True

    def __repr__(self) -> str:
        return (
            f"TmTransferFrame(sc_id={self.spacecraft_id}, vc_id={self.virtual_channel_id}, "
            f"mcfc={self.master_channel_frame_count}, vcfc={self.virtual_channel_frame_count}, "
            f"len={self.get_length()}, ocf={self.ocf_present}, fecf={self.is_fecf_present()}, "
            f"sh_pres={self.secondary_header_present}, sync={self.synchronisation_flag}, "
            f"fhp={self.first_header_pointer}, idle={self.is_idle_frame()}, "
            f"data_len={self.get_data_field_length()})"
        )

    def __str__(self) -> str:
        return self.__repr__()

# Example Usage (for testing during development)
if __name__ == '__main__':
    # Construct a dummy TM frame byte string (replace with actual frame data for testing)
    # This is a highly simplified example, many fields might not be standard-compliant
    # Primary Header (6 bytes):
    # Version (00), SCID (0x123 -> 0100100011), VCID (0x4 -> 100), OCF (1) -> 00 0100100011 100 1 = 0x123D
    # MCFC (0xAA)
    # VCFC (0xBB)
    # SH_Pres (1), Sync (1), POF (0), SLID (00), FHP (0x123) -> 11000 00100100011 = 0xC243
    header_bytes = struct.pack(">HBBH", 0x123D, 0xAA, 0xBB, 0xC243) # 6 bytes

    # Secondary Header (optional, 1 byte ID + data_length bytes)
    # SH Ver (01), SH Data Len (2) -> 01000010 = 0x42
    # SH Data (DD EE)
    sh_id_byte = bytes([0x42])
    sh_data_bytes = bytes([0xDD, 0xEE])
    secondary_header_bytes = sh_id_byte + sh_data_bytes # 3 bytes

    # Security Header (optional)
    sec_header_bytes = bytes([0x5A, 0x5A]) # 2 bytes

    # Data Field
    data_field_bytes = b"TestData1234567890" # 20 bytes

    # OCF (optional, 4 bytes)
    ocf_bytes = bytes([0x01, 0x02, 0x03, 0x04])

    # Security Trailer (optional)
    sec_trailer_bytes = bytes([0xA5, 0xA5]) # 2 bytes

    # FECF (optional, 2 bytes)
    fecf_bytes = bytes([0xFF, 0xFF])

    # Construct frame with all optional fields present
    frame_data_full = header_bytes + secondary_header_bytes + sec_header_bytes + \
                      data_field_bytes + ocf_bytes + sec_trailer_bytes + fecf_bytes
    print(f"Full frame length: {len(frame_data_full)}")

    try:
        tm_frame_full = TmTransferFrame(frame_data_full, fecf_present=True, security_header_length=len(sec_header_bytes), security_trailer_length=len(sec_trailer_bytes))
        print(f"Parsed full TM frame: {tm_frame_full}")
        print(f"  Version: {tm_frame_full.transfer_frame_version_number}")
        print(f"  SCID: {tm_frame_full.spacecraft_id}")
        print(f"  VCID: {tm_frame_full.virtual_channel_id}")
        print(f"  OCF Present: {tm_frame_full.is_ocf_present()}") # From AbstractTransferFrame
        print(f"  MCFC: {tm_frame_full.master_channel_frame_count}")
        print(f"  VCFC: {tm_frame_full.virtual_channel_frame_count}")
        print(f"  SH Present: {tm_frame_full.secondary_header_present}")
        print(f"  Sync Flag: {tm_frame_full.synchronisation_flag}")
        print(f"  Packet Order Flag: {tm_frame_full.packet_order_flag}")
        print(f"  Segment Len ID: {tm_frame_full.segment_length_identifier}")
        print(f"  FHP: {hex(tm_frame_full.first_header_pointer)}")
        print(f"  Is Idle: {tm_frame_full.is_idle_frame()}")
        print(f"  No Start Packet: {tm_frame_full.no_start_packet}")
        if tm_frame_full.secondary_header_present:
            print(f"  SH Version: {tm_frame_full.secondary_header_version_number}")
            print(f"  SH Data Length: {tm_frame_full.secondary_header_data_length}")
            print(f"  SH Copy: {tm_frame_full.get_secondary_header_copy().hex()}")
        print(f"  Security Header Length: {tm_frame_full.security_header_length}")
        print(f"  Security Trailer Length: {tm_frame_full.security_trailer_length}")
        print(f"  Data Field Length: {tm_frame_full.get_data_field_length()}")
        print(f"  Data Field Copy: {tm_frame_full.get_data_field_copy().hex()} (len {len(tm_frame_full.get_data_field_copy())})")
        if tm_frame_full.is_ocf_present():
            print(f"  OCF Copy: {tm_frame_full.get_ocf_copy().hex()}")
        if tm_frame_full.is_fecf_present():
            print(f"  FECF: {hex(tm_frame_full.get_fecf())}")
        print(f"  Security Header Copy: {tm_frame_full.get_security_header_copy().hex()}")
        print(f"  Security Trailer Copy: {tm_frame_full.get_security_trailer_copy().hex()}")
        print(f"  Frame Valid: {tm_frame_full.is_valid()}")
        print(f"  Frame Length: {tm_frame_full.get_length()}")

        # Frame without OCF, SecTrailer, FECF, SecHeader, SecondaryHeader
        frame_data_minimal = header_bytes + data_field_bytes
        # Update primary header: OCF Present (0), SH_Pres (0)
        # 00 0100100011 100 0 = 0x123C
        # 01000 00100100011 = 0x4243 (Sync=1, POF=0, SLID=0, FHP=0x243)
        min_header_bytes = struct.pack(">HBBH", 0x123C, 0xAA, 0xBB, 0x4243)
        frame_data_minimal = min_header_bytes + data_field_bytes
        tm_frame_minimal = TmTransferFrame(frame_data_minimal, fecf_present=False)
        print(f"Parsed minimal TM frame: {tm_frame_minimal}")
        print(f"  Data Field Length: {tm_frame_minimal.get_data_field_length()}")
        print(f"  Data Field Copy: {tm_frame_minimal.get_data_field_copy().hex()}")
        print(f"  OCF Present: {tm_frame_minimal.is_ocf_present()}")
        print(f"  SH Present: {tm_frame_minimal.secondary_header_present}")


        # Idle frame test
        # FHP = 2046 (0x7FE)
        idle_header_bytes = struct.pack(">HBBH", 0x123C, 0xAA, 0xBB, (0x4000 | 0x07FE)) # Sync=1, FHP=IDLE
        idle_frame_data = idle_header_bytes + bytes([0]*(len(data_field_bytes))) # Idle frames have idle pattern in data field
        tm_idle_frame = TmTransferFrame(idle_frame_data, fecf_present=False)
        print(f"Parsed idle TM frame: {tm_idle_frame}")
        print(f"  Is Idle: {tm_idle_frame.is_idle_frame()}")
        print(f"  FHP: {hex(tm_idle_frame.first_header_pointer)}")

    except ValueError as e:
        print(f"Error constructing TM frame: {e}")
    except IllegalStateException as e:
        print(f"Error accessing TM frame field: {e}")

</tbody>
</table>
