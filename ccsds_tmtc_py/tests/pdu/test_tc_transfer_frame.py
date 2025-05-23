import unittest
import struct
from ccsds_tmtc_py.datalink.pdu.tc_transfer_frame import TcTransferFrame, FrameType, ControlCommandType, SequenceFlagType as TcFrameSequenceFlagType
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException


class TestTcTransferFrame(unittest.TestCase):
  def _construct_tc_header(self, scid=0x123, vcid=1, frame_len_val=5, bypass=0, control_cmd=0, vc_frame_count=0):
    hdr1 = (0 << 14) | (bypass << 13) | (control_cmd << 12) | scid # TFVN=0
    hdr2 = (vcid << 10) | ((frame_len_val -1) & 0x03FF) # length field is len-1
    return struct.pack(">HHB", hdr1, hdr2, vc_frame_count)

  def test_construct_ad_frame_no_segment(self):
    payload = b"ad_payload"
    header = self._construct_tc_header(frame_len_val=5+len(payload))
    frame_bytes = header + payload
    # segmented_fn returns False if VC is not configured for segmented service
    tc_frame = TcTransferFrame(frame_bytes, lambda vc_id: False, fecf_present=False)
    self.assertEqual(tc_frame.transfer_frame_version_number, 0)
    self.assertEqual(tc_frame.frame_type, FrameType.AD)
    self.assertFalse(tc_frame.segmented)
    self.assertEqual(tc_frame.get_data_field_copy(), payload)
    self.assertEqual(tc_frame.frame_length, 5+len(payload))

  def test_construct_ad_frame_segmented(self):
    seg_hdr_byte = (TcFrameSequenceFlagType.FIRST.value << 6) | 0x0A # MAP ID 10
    payload = b"segmented_payload"
    header = self._construct_tc_header(frame_len_val=5+1+len(payload)) # +1 for seg header
    frame_bytes = header + bytes([seg_hdr_byte]) + payload
    # segmented_fn returns True if VC is configured for segmented service
    tc_frame = TcTransferFrame(frame_bytes, lambda vc_id: True, fecf_present=False)
    self.assertTrue(tc_frame.segmented)
    self.assertEqual(tc_frame.map_id, 0x0A)
    self.assertEqual(tc_frame.sequence_flag, TcFrameSequenceFlagType.FIRST)
    self.assertEqual(tc_frame.get_data_field_copy(), payload)

  def test_construct_bc_frame_unlock(self):
    cmd_data = b"\x00"
    # For BC frame, bypass flag is 0 (standard says "shall be set to '0' for Type-BC frames")
    header = self._construct_tc_header(bypass=0, control_cmd=1, frame_len_val=5+len(cmd_data))
    frame_bytes = header + cmd_data
    tc_frame = TcTransferFrame(frame_bytes, lambda vc_id: False, fecf_present=False)
    self.assertEqual(tc_frame.frame_type, FrameType.BC)
    self.assertEqual(tc_frame.control_command_type, ControlCommandType.UNLOCK)
    self.assertEqual(tc_frame.get_data_field_copy(), cmd_data)

  def test_construct_bc_frame_set_vr(self):
    set_vr_val = 0xAB
    cmd_data = bytes([0x82, 0x00, set_vr_val])
    header = self._construct_tc_header(bypass=0, control_cmd=1, frame_len_val=5+len(cmd_data))
    frame_bytes = header + cmd_data
    tc_frame = TcTransferFrame(frame_bytes, lambda vc_id: False, fecf_present=False)
    self.assertEqual(tc_frame.frame_type, FrameType.BC)
    self.assertEqual(tc_frame.control_command_type, ControlCommandType.SET_VR)
    self.assertEqual(tc_frame.set_vr_value, set_vr_val)
    self.assertEqual(tc_frame.get_data_field_copy(), cmd_data)

  def test_construct_bd_frame(self):
    payload = b"bd_payload"
    # BD frame: Bypass=1, ControlCmd=0
    header = self._construct_tc_header(bypass=1, control_cmd=0, frame_len_val=5+len(payload))
    frame_bytes = header + payload
    tc_frame = TcTransferFrame(frame_bytes, lambda vc_id: False, fecf_present=False) # Not segmented for this BD test
    self.assertEqual(tc_frame.frame_type, FrameType.BD)
    self.assertFalse(tc_frame.segmented) # As segmented_fn returns False
    self.assertEqual(tc_frame.get_data_field_copy(), payload)

  def test_with_security_and_fecf(self):
    sec_header = b"\xDE\xAD"
    sec_trailer = b"\xBE\xEF"
    payload = b"secure_payload"
    # AD frame, not segmented, with security and FECF
    header_len = 5
    seg_hdr_len = 0
    data_len = len(payload)
    fecf_len = 2
    
    total_frame_len = header_len + seg_hdr_len + len(sec_header) + data_len + len(sec_trailer) + fecf_len
    header = self._construct_tc_header(frame_len_val=total_frame_len)
    frame_bytes = header + sec_header + payload + sec_trailer + b"\xCA\xFE" # Dummy FECF

    tc_frame = TcTransferFrame(frame_bytes, 
                               lambda vc_id: False, # Not segmented
                               fecf_present=True, 
                               security_header_length=len(sec_header), 
                               security_trailer_length=len(sec_trailer))
    
    self.assertEqual(tc_frame.security_header_length, len(sec_header))
    self.assertEqual(tc_frame.security_trailer_length, len(sec_trailer))
    self.assertEqual(tc_frame.get_security_header_copy(), sec_header)
    self.assertEqual(tc_frame.get_security_trailer_copy(), sec_trailer)
    self.assertEqual(tc_frame.get_data_field_copy(), payload)
    self.assertTrue(tc_frame.is_fecf_present())
    self.assertEqual(tc_frame.get_fecf(), 0xCAFE)

  def test_invalid_tfvn(self):
    hdr1_bad_tfvn = (1 << 14) # TFVN=1 for TC is bad
    header = struct.pack(">HHB", hdr1_bad_tfvn, 0, 0) + b"\x00\x00" # Min length (5)
    with self.assertRaisesRegex(ValueError, "Invalid TC Transfer Frame Version Number"):
        TcTransferFrame(header, lambda vc_id: False, False)

  def test_length_mismatch(self):
    payload = b"data"
    # Frame len val in header says 5 + 3 = 8 bytes. Actual is 5 + 4 = 9 bytes.
    header = self._construct_tc_header(frame_len_val=5+len(payload)-1) 
    frame_bytes = header + payload
    with self.assertRaisesRegex(ValueError, "Frame length field value .* does not match actual frame length"):
        TcTransferFrame(frame_bytes, lambda vc_id: False, False)

if __name__ == '__main__':
    unittest.main()
