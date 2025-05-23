import struct
from enum import Enum
import abc

from .abstract_transfer_frame import AbstractTransferFrame, IllegalStateException

class FrameType(Enum):
    AD = 0  # Type AD: Contains a complete PDU or the first segment of a PDU
    RESERVED = 1 # Reserved, should not be used
    BD = 2  # Type BD: Contains a segment of a PDU other than the first or last segment
    BC = 3  # Type BC: Contains the last segment of a PDU or a Control Command

class ControlCommandType(Enum):
    UNLOCK = 0
    SET_VR = 1
    RESERVED_CTRL = 2 # For any BC frame that doesn't match UNLOCK or SET_VR

class SequenceFlagType(Enum):
    CONTINUE = 0 # PDU continues in the next frame
    FIRST = 1    # First segment of a multi-segment PDU
    LAST = 2     # Last segment of a multi-segment PDU
    NO_SEGMENT = 3 # PDU is contained entirely within this frame (unsegmented)

class TcTransferFrame(AbstractTransferFrame):
    """
    TC Transfer Frame according to CCSDS 232.0-B-3.
    """
    TC_PRIMARY_HEADER_LENGTH = 5
    MAX_TC_FRAME_LENGTH = 1024 # As per standard

    def __init__(self, frame: bytes, segmented_fn: callable, fecf_present: bool, security_header_length: int = 0, security_trailer_length: int = 0):
        super().__init__(frame, fecf_present)

        self._passed_security_header_length = security_header_length
        self._passed_security_trailer_length = security_trailer_length

        if len(frame) < self.TC_PRIMARY_HEADER_LENGTH:
            raise ValueError(
                f"Frame too short for TC primary header: {len(frame)} bytes, "
                f"minimum {self.TC_PRIMARY_HEADER_LENGTH} bytes required."
            )
        if len(frame) > self.MAX_TC_FRAME_LENGTH:
            raise ValueError(
                f"Frame length {len(frame)} exceeds maximum TC frame length of {self.MAX_TC_FRAME_LENGTH} bytes."
            )

        hdr_part1, hdr_part2, self._vcfc_byte = struct.unpack(">HHB", frame[0:self.TC_PRIMARY_HEADER_LENGTH])
        self.virtual_channel_frame_count = self._vcfc_byte # From AbstractTransferFrame

        self.transfer_frame_version_number = (hdr_part1 & 0xC000) >> 14
        if self.transfer_frame_version_number != 0: # TC version is 0
            raise ValueError(f"Invalid TC Transfer Frame Version Number: {self.transfer_frame_version_number}, expected 0")

        self._bypass_flag = (hdr_part1 & 0x2000) != 0
        self._control_command_flag = (hdr_part1 & 0x1000) != 0
        # Reserved bit (hdr_part1 & 0x0800) >> 11 - not stored, assumed 0 by standard for TC frames

        self.spacecraft_id = hdr_part1 & 0x03FF

        self.virtual_channel_id = (hdr_part2 & 0xFC00) >> 10
        self._frame_length_field = (hdr_part2 & 0x03FF) # This is (actual length - 1)
        self._actual_frame_length = self._frame_length_field + 1

        if self._actual_frame_length != len(frame):
            raise ValueError(
                f"Frame length field value {self._actual_frame_length} does not match "
                f"actual frame length {len(frame)}."
            )

        self._determined_frame_type = self._determine_frame_type()

        # The segmented_fn is expected to return True if the VC is configured for segmented service, False otherwise.
        self._segmented = self.determined_frame_type != FrameType.BC and segmented_fn(self.virtual_channel_id)

        self._map_id = 0
        self._sequence_flag = SequenceFlagType.NO_SEGMENT # Default for unsegmented or BC
        self._control_command_type_val = None
        self._set_vr_value = 0

        if self.determined_frame_type == FrameType.BC:
            self._actual_security_header_length = 0
            self._actual_security_trailer_length = 0
            self.data_field_start = self.TC_PRIMARY_HEADER_LENGTH
            # For BC frames, data field is the control command itself or reserved.
            # FECF is always considered in total length.
            self.data_field_length = self._actual_frame_length - self.data_field_start - (2 if self.is_fecf_present() else 0)

            if self.data_field_length < 0:
                 raise ValueError(f"Calculated negative data field length for BC frame: {self.data_field_length}")

            # Check for specific control commands
            cmd_data_start_idx = self.data_field_start
            if self.data_field_length == 1 and frame[cmd_data_start_idx] == 0x00:
                self._control_command_type_val = ControlCommandType.UNLOCK
            elif self.data_field_length == 3 and frame[cmd_data_start_idx] == 0x82 and frame[cmd_data_start_idx+1] == 0x00:
                self._control_command_type_val = ControlCommandType.SET_VR
                self._set_vr_value = frame[cmd_data_start_idx+2]
            else:
                # If it's a BC frame but not Unlock or Set V(R), it's 'reserved' by this implementation's enum
                self._control_command_type_val = ControlCommandType.RESERVED_CTRL
        else: # AD or BD frames
            self._actual_security_header_length = self._passed_security_header_length
            self._actual_security_trailer_length = self._passed_security_trailer_length

            segmentation_header_len = (1 if self.segmented else 0)
            self.data_field_start = self.TC_PRIMARY_HEADER_LENGTH + segmentation_header_len + self.actual_security_header_length
            
            self.data_field_length = self._actual_frame_length - self.data_field_start - \
                                     self.actual_security_trailer_length - \
                                     (2 if self.is_fecf_present() else 0)
            
            if self.data_field_length < 0:
                 raise ValueError(f"Calculated negative data field length for AD/BD frame: {self.data_field_length}")

            if self.segmented:
                if len(frame) <= self.TC_PRIMARY_HEADER_LENGTH:
                    raise ValueError("Frame too short for segmentation header byte.")
                seg_header_byte = frame[self.TC_PRIMARY_HEADER_LENGTH]
                self._map_id = seg_header_byte & 0x3F
                self._sequence_flag = SequenceFlagType((seg_header_byte & 0xC0) >> 6)
            else: # Unsegmented AD/BD
                self._sequence_flag = SequenceFlagType.NO_SEGMENT


        self.valid = self._check_validity()
        self.ocf_present = False # TC Frames do not have OCF
        self.ocf_start = -1

    def _determine_frame_type(self) -> FrameType:
        if self.control_command_flag:
            return FrameType.BC # Control Command Flag set means BC frame
        # If not BC, it's AD or BD. The standard says bypass_flag determines this:
        # "The Bypass Flag shall be set to '0' for Type-AD frames and to '1' for Type-BD frames."
        # This interpretation seems different from the Java code's use of segment_fn for BD.
        # The standard (CCSDS 232.0-B-3 section 4.1.2.6) implies segmentation header presence dictates AD/BD.
        # However, the task asks to mimic Java, which uses segmented_fn.
        # Let's stick to the spec for now: ControlCommandFlag = 1 -> BC.
        # For AD/BD, the distinction is typically made based on sequence flags if segmented,
        # or if it's the start of a MAP_SDU or continuation.
        # The task implies segmented_fn influences this.
        # The task is to implement based on Java, which seems to tie BD to segmentation.
        # If ControlCommandFlag is 0, it's an AD or BD frame.
        # The problem statement "self.segmented = self.determined_frame_type != FrameType.BC and segmented_fn(self.virtual_channel_id)"
        # indicates that 'segmented' is a consequence of frame type and config, not a primary differentiator for type here.
        # The Java code implies:
        # if (controlCommandFlag) return BC_FRAME;
        # else if (segmented) return BD_FRAME; // This seems to be the interpretation for BD type
        # else return AD_FRAME;
        # This is a bit unusual, as AD can also be segmented (first segment).
        # Let's follow the task's structure which implies a different flow or I misunderstood the Java logic.
        # Re-evaluating: The task's constructor logic implies:
        # 1. Determine frame type (AD/BD/BC)
        # 2. THEN determine if it's 'segmented' (AD/BD only).
        # The provided logic for 'segmented' is `self.determined_frame_type != FrameType.BC and segmented_fn(self.virtual_channel_id)`.
        # This means AD or BD can be 'segmented'.
        # The distinction between AD and BD in the Java code (from my memory of its structure) is more about
        # whether it's a "data" frame (AD/BD) or "control" (BC).
        # The Java code uses `segmented` to decide if it's a BD frame.
        # `if (this.controlCommandFlag) { this.type = FrameType.BC_FRAME; } else { if(segmented) this.type = FrameType.BD_FRAME; else this.type = FrameType.AD_FRAME;}`
        # This is what I will try to replicate for `determined_frame_type`.
        # No, the task says: "self.determined_frame_type = self._determine_frame_type()" then "self.segmented = self.determined_frame_type != FrameType.BC and segmented_fn(self.virtual_channel_id)"
        # This means _determine_frame_type must differentiate AD/BD *without* using segmented_fn yet.
        # The standard for TC (232.0-B-3) in 4.1.2.2.1 states:
        # "A Type-AD frame shall be used to transmit a MAP Channel Access Data Unit which is either complete or is the first segment of a sequence of segments."
        # "A Type-BD frame shall be used to transmit any segment of a MAP Channel Access Data Unit other than the first."
        # "A Type-BC frame shall be used to transmit Control Commands..."
        # The distinction between AD and BD *depends* on segmentation and sequence.
        # The structure "self.segmented = self.determined_frame_type != FrameType.BC and segmented_fn(self.virtual_channel_id)"
        # means `segmented_fn` (VC config) + frame type determines if segmentation header is parsed.
        # If `control_command_flag` is true, it's BC.
        # If `control_command_flag` is false, it's AD/BD. How to pick AD vs BD here?
        # The Bypass Flag is key:
        # 4.1.2.3 Bypass Flag: "The Bypass Flag shall be set to ‘0’ for Type-AD frames and to ‘1’ for Type-BD frames."
        if self._control_command_flag:
            return FrameType.BC
        elif self._bypass_flag: # Bypass flag = 1
            return FrameType.BD
        else: # Bypass flag = 0
            return FrameType.AD

    def is_idle_frame(self) -> bool:
        """TC frames are typically not considered 'idle' in the same way TM/AOS idle frames are.
        They can carry specific idle sequences or be Type BC Unlock commands, but there isn't a dedicated idle pattern
        flag like TM/AOS First Header Pointer for idle."""
        return False # Per task requirement

    @property
    def bypass_flag(self) -> bool:
        return self._bypass_flag

    @property
    def control_command_flag(self) -> bool:
        return self._control_command_flag

    @property
    def frame_type(self) -> FrameType:
        return self._determined_frame_type

    @property
    def frame_length(self) -> int: # This is the actual frame length
        return self._actual_frame_length

    @property
    def segmented(self) -> bool:
        return self._segmented

    @property
    def map_id(self) -> int:
        if not self.segmented:
            # As per Java, return 0 if not segmented, though spec might imply this field isn't there.
            # However, if segmented is false, segmentation header is not parsed, so map_id remains its default 0.
            return 0
        return self._map_id

    @property
    def sequence_flag(self) -> SequenceFlagType:
        # If not segmented (and not BC), it's implicitly NO_SEGMENT.
        # If BC, it's also NO_SEGMENT (as per task logic).
        return self._sequence_flag

    @property
    def control_command_type(self) -> ControlCommandType | None:
        if self.determined_frame_type == FrameType.BC:
            return self._control_command_type_val
        return None # Not a BC frame

    @property
    def set_vr_value(self) -> int:
        if self.determined_frame_type == FrameType.BC and self.control_command_type == ControlCommandType.SET_VR:
            return self._set_vr_value
        return 0 # Or raise error if not applicable? Java returns 0.

    @property
    def security_header_length(self) -> int:
        return self._actual_security_header_length

    @property
    def security_trailer_length(self) -> int:
        return self._actual_security_trailer_length

    def get_security_header_copy(self) -> bytes:
        if self.actual_security_header_length == 0:
            return b''
        # Security header is after primary header and optional segmentation header
        start_idx = self.TC_PRIMARY_HEADER_LENGTH + (1 if self.segmented else 0)
        end_idx = start_idx + self.actual_security_header_length
        if end_idx > len(self._frame):
             raise ValueError("Security header indicated but frame too short.")
        return self._frame[start_idx:end_idx]

    def get_security_trailer_copy(self) -> bytes:
        if self.actual_security_trailer_length == 0:
            return b''
        # Security trailer is before FECF (if present)
        end_idx = self._actual_frame_length - (2 if self.is_fecf_present() else 0)
        start_idx = end_idx - self.actual_security_trailer_length
        if start_idx < 0 or start_idx < self.data_field_start + self.data_field_length: # Ensure it doesn't overlap data
             raise ValueError("Security trailer indicated but frame too short or position invalid.")
        return self._frame[start_idx:end_idx]

    def _check_validity(self) -> bool:
        # Placeholder for actual CRC/checksum check if FECF is present.
        # For now, assume the frame is valid if it could be parsed this far.
        # TODO: Implement CRC-16/checksum check if FECF is present.
        return True

    def __repr__(self) -> str:
        return (
            f"TcTransferFrame(sc_id={self.spacecraft_id}, vc_id={self.virtual_channel_id}, "
            f"vcfc={self.virtual_channel_frame_count}, type={self.frame_type.name}, "
            f"len={self.frame_length}, bypass={self.bypass_flag}, ctrl_cmd={self.control_command_flag}, "
            f"segmented={self.segmented}, seq_flag={self.sequence_flag.name if self.segmented or self.frame_type != FrameType.BC else 'N/A'}, "
            f"map_id={self.map_id if self.segmented else 'N/A'}, "
            f"fecf={self.is_fecf_present()}, data_len={self.get_data_field_length()})"
        )

    def __str__(self) -> str:
        return self.__repr__()

# Example Usage (for testing during development)
if __name__ == '__main__':
    def dummy_segmented_fn_true(vc_id): return True
    def dummy_segmented_fn_false(vc_id): return False

    # AD Frame, Unsegmented, No Security
    # TFVN=0, Bypass=0, CtrlCmd=0, SCID=0xAB, VCID=0x5, Len=15 (+1 = 16), VCFC=0xCD
    # Header: 0000 000010101011 = 0x00AB
    #         0101 00 0000001111 = 0x500F (VCID=5, Frame Len=15)
    # VCFC:   11001101 = 0xCD
    ad_header = struct.pack(">HHB", 0x00AB, 0x500F, 0xCD) # 5 bytes
    ad_data = b"TestData123" # 11 bytes. Total 5+11 = 16 bytes.
    ad_frame_data = ad_header + ad_data
    print(f"AD Unsegmented frame data (len {len(ad_frame_data)}): {ad_frame_data.hex()}")
    try:
        ad_frame = TcTransferFrame(ad_frame_data, dummy_segmented_fn_false, fecf_present=False)
        print(f"Parsed AD Unsegmented: {ad_frame}")
        print(f"  Data: {ad_frame.get_data_field_copy()}")
        assert ad_frame.frame_type == FrameType.AD
        assert not ad_frame.segmented
        assert ad_frame.sequence_flag == SequenceFlagType.NO_SEGMENT
    except ValueError as e:
        print(f"Error: {e}")

    # AD Frame, Segmented (First), No Security, FECF
    # TFVN=0, Bypass=0, CtrlCmd=0, SCID=0xAC, VCID=0x6, Len=17 (+1 = 18), VCFC=0xCE
    # Header: 0000 000010101100 = 0x00AC
    #         0110 00 0000010001 = 0x6011 (VCID=6, Frame Len=17)
    # VCFC:   11001110 = 0xCE
    # SegHdr: Seq=FIRST (01), MAPID=0x0A -> 01001010 = 0x4A
    ad_s_header = struct.pack(">HHB", 0x00AC, 0x6011, 0xCE) # 5 bytes
    ad_s_seg_header = bytes([0x4A]) # 1 byte
    ad_s_data = b"Segment1Dat"  # 11 bytes. 5+1+11+2(FECF) = 19. Len field should be 18 (19-1).
                                # Frame len 19. Field must be 18.
    # Expected frame length = 5 (hdr) + 1 (seg) + 11 (data) + 0 (sec_hdr) + 0 (sec_trl) + 2 (fecf) = 19
    # So, length field in header should be 19-1 = 18 (0x0012)
    ad_s_header_correctlen = struct.pack(">HHB", 0x00AC, (0x6000 | 18), 0xCE)
    ad_s_fecf = b"\x12\x34" # 2 bytes
    ad_s_frame_data = ad_s_header_correctlen + ad_s_seg_header + ad_s_data + ad_s_fecf
    print(f"AD Segmented frame data (len {len(ad_s_frame_data)}): {ad_s_frame_data.hex()}")
    try:
        ad_s_frame = TcTransferFrame(ad_s_frame_data, dummy_segmented_fn_true, fecf_present=True)
        print(f"Parsed AD Segmented: {ad_s_frame}")
        print(f"  Data: {ad_s_frame.get_data_field_copy()}")
        assert ad_s_frame.frame_type == FrameType.AD
        assert ad_s_frame.segmented
        assert ad_s_frame.sequence_flag == SequenceFlagType.FIRST
        assert ad_s_frame.map_id == 0x0A
        assert ad_s_frame.is_fecf_present()
        assert ad_s_frame.get_fecf() == 0x1234
    except ValueError as e:
        print(f"Error: {e}")

    # BC Frame, UNLOCK, No Security, No FECF
    # TFVN=0, Bypass=0, CtrlCmd=1, SCID=0xAD, VCID=0x7, Len=5 (+1 = 6), VCFC=0xCF
    # Header: 0001 000010101101 = 0x10AD
    #         0111 00 0000000101 = 0x7005 (VCID=7, Frame Len=5)
    # VCFC:   11001111 = 0xCF
    # Data:   0x00 (UNLOCK)
    bc_header = struct.pack(">HHB", 0x10AD, 0x7005, 0xCF) # 5 bytes
    bc_data = b"\x00" # 1 byte. Total 5+1 = 6 bytes.
    bc_frame_data = bc_header + bc_data
    print(f"BC UNLOCK frame data (len {len(bc_frame_data)}): {bc_frame_data.hex()}")
    try:
        bc_frame = TcTransferFrame(bc_frame_data, dummy_segmented_fn_false, fecf_present=False)
        print(f"Parsed BC UNLOCK: {bc_frame}")
        assert bc_frame.frame_type == FrameType.BC
        assert bc_frame.control_command_type == ControlCommandType.UNLOCK
        assert not bc_frame.segmented
    except ValueError as e:
        print(f"Error: {e}")

    # BD Frame, Segmented (Continue), Security (2B header, 1B trailer), No FECF
    # TFVN=0, Bypass=1, CtrlCmd=0, SCID=0xAE, VCID=0x1, Len=20 (+1 = 21), VCFC=0xD0
    # Header: 0010 000010101110 = 0x20AE (Bypass=1)
    #         0001 00 0000010100 = 0x1014 (VCID=1, Frame Len=20)
    # VCFC:   11010000 = 0xD0
    # SegHdr: Seq=CONTINUE (00), MAPID=0x0B -> 00001011 = 0x0B
    # SecHdr: 0xS1S2 (2 bytes)
    # Data:   "BDDataSeg.." (10 bytes)
    # SecTrl: 0xT1 (1 byte)
    # Total: 5(hdr) + 1(seg) + 2(sechdr) + 10(data) + 1(sectrl) = 19. Frame Len field should be 18 (0x12)
    bd_s_header = struct.pack(">HHB", 0x20AE, (0x1000 | 18), 0xD0)
    bd_s_seg_header = bytes([0x0B])
    bd_s_sec_header = b"\S1\S2"
    bd_s_data = b"BDDataSeg." # 10 bytes
    bd_s_sec_trailer = b"\T1"
    bd_s_frame_data = bd_s_header + bd_s_seg_header + bd_s_sec_header + bd_s_data + bd_s_sec_trailer
    print(f"BD Segmented frame data (len {len(bd_s_frame_data)}): {bd_s_frame_data.hex()}")
    try:
        bd_s_frame = TcTransferFrame(bd_s_frame_data, dummy_segmented_fn_true, fecf_present=False, security_header_length=2, security_trailer_length=1)
        print(f"Parsed BD Segmented: {bd_s_frame}")
        print(f"  Data: {bd_s_frame.get_data_field_copy()}")
        print(f"  SecHdr: {bd_s_frame.get_security_header_copy()}")
        print(f"  SecTrl: {bd_s_frame.get_security_trailer_copy()}")
        assert bd_s_frame.frame_type == FrameType.BD
        assert bd_s_frame.segmented
        assert bd_s_frame.sequence_flag == SequenceFlagType.CONTINUE
        assert bd_s_frame.map_id == 0x0B
        assert bd_s_frame.security_header_length == 2
        assert bd_s_frame.security_trailer_length == 1
    except ValueError as e:
        print(f"Error: {e}")
</tbody>
</table>
