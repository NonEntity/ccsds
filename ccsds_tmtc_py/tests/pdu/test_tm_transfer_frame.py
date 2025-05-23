import unittest
import struct
from ccsds_tmtc_py.datalink.pdu.tm_transfer_frame import TmTransferFrame
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException

class TestTmTransferFrame(unittest.TestCase):
  def test_construct_and_parse_primary_header_no_sh_no_ocf_no_fecf(self):
    # TFVN=0, SCID=0xAB, VCID=3, OCF=absent, MCFC=100, VCFC=200, SH=absent, Sync=0, PktOrder=0, SegLenID=3 (no seg), FHP=2047 (No Pkt)
    hdr_part1 = (0x00 << 14) | (0xAB << 4) | (3 << 1) | 0 # No OCF
    mcfc = 100
    vcfc = 200
    hdr_part2 = (0 << 15) | (0 << 14) | (0 << 13) | (3 << 11) | 2047 # No SH, No Sync, No PktOrder, NoSeg, FHP=NoPkt
    # Frame must be long enough to contain header + FHP logic.
    # Minimum data length for a frame with FHP != IDLE is 0 if FHP points to end of frame.
    # If FHP is NO_PACKET or IDLE, data field length can be 0.
    # Data field start for this config is TM_PRIMARY_HEADER_LENGTH (6).
    # Data field length = total_len - 6. If total_len is 6, data_len is 0.
    frame_bytes = struct.pack(">HBBH", hdr_part1, mcfc, vcfc, hdr_part2) + b"somedata" 
    tm_frame = TmTransferFrame(frame_bytes, fecf_present=False)
    self.assertEqual(tm_frame.transfer_frame_version_number, 0)
    self.assertEqual(tm_frame.spacecraft_id, 0xAB)
    self.assertEqual(tm_frame.virtual_channel_id, 3)
    self.assertFalse(tm_frame.ocf_present) # ocf_present is a parsed attribute
    self.assertEqual(tm_frame.master_channel_frame_count, 100)
    self.assertEqual(tm_frame.virtual_channel_frame_count, 200)
    self.assertFalse(tm_frame.secondary_header_present)
    self.assertFalse(tm_frame.synchronisation_flag)
    self.assertFalse(tm_frame.packet_order_flag)
    self.assertEqual(tm_frame.segment_length_identifier, 3)
    self.assertEqual(tm_frame.first_header_pointer, 2047)
    self.assertFalse(tm_frame.is_idle_frame())
    self.assertTrue(tm_frame.no_start_packet)
    self.assertEqual(tm_frame.data_field_start, TmTransferFrame.TM_PRIMARY_HEADER_LENGTH)
    self.assertEqual(tm_frame.get_data_field_copy(), b"somedata")

  def test_with_secondary_header(self):
    hdr_part1 = (0x00 << 14) | (0xCD << 4) | (1 << 1) | 0 # No OCF
    hdr_part2 = (1 << 15) | (0 << 14) | (0 << 13) | (3 << 11) | 10 # SH present, FHP=10
    sh_id_len = (0b00 << 6) | 3 # Version 0, SH data length 3 bytes
    sh_data = b"\x01\x02\x03"
    user_data = b"userdata"
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0, 0, hdr_part2) + bytes([sh_id_len]) + sh_data + user_data
    tm_frame = TmTransferFrame(frame_bytes, fecf_present=False)
    self.assertTrue(tm_frame.secondary_header_present)
    self.assertEqual(tm_frame.secondary_header_version_number, 0)
    self.assertEqual(tm_frame.secondary_header_data_length, 3)
    self.assertEqual(tm_frame.get_secondary_header_copy(), sh_data)
    expected_df_start = TmTransferFrame.TM_PRIMARY_HEADER_LENGTH + 1 + 3 # PH + SH_ID_Byte + SH_Data
    self.assertEqual(tm_frame.data_field_start, expected_df_start)
    self.assertEqual(tm_frame.get_data_field_copy(), user_data)

  def test_with_ocf_and_fecf(self):
    hdr_part1 = (0x00 << 14) | (0xEF << 4) | (2 << 1) | 1 # OCF present
    hdr_part2 = (0 << 15) # No SH, FHP=0 for simplicity
    user_data = b"testdata123"
    ocf_data = b"\xCA\xFE\xBA\xBE"
    fecf_data = b"\xDE\xAD"
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0, 0, hdr_part2) + user_data + ocf_data + fecf_data
    tm_frame = TmTransferFrame(frame_bytes, fecf_present=True) # OCF presence derived from frame header bit
    self.assertTrue(tm_frame.ocf_present)
    self.assertEqual(tm_frame.get_ocf_copy(), ocf_data)
    self.assertTrue(tm_frame.is_fecf_present())
    self.assertEqual(tm_frame.get_fecf(), struct.unpack(">H", fecf_data)[0])
    self.assertEqual(tm_frame.get_data_field_copy(), user_data)
    self.assertTrue(tm_frame.is_valid()) # Placeholder _check_validity returns True

  def test_idle_frame(self):
    hdr_part1 = (0x00 << 14) | (0x00 << 4) | (0x00 << 1) | 0 # SCID=0, VCID=0, No OCF
    hdr_part2 = (0 << 15) | (0 << 14) | (0 << 13) | (3 << 11) | TmTransferFrame.TM_FIRST_HEADER_POINTER_IDLE # No SH, No Sync, No Seg, FHP=IDLE
    # Minimal frame for idle: just primary header. Data field length will be 0.
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2) 
    tm_frame = TmTransferFrame(frame_bytes, fecf_present=False)
    self.assertTrue(tm_frame.is_idle_frame())
    self.assertEqual(tm_frame.get_data_field_length(), 0)

  def test_invalid_tfvn(self):
    hdr_part1 = (1 << 14) # Invalid TFVN
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0,0,0)
    with self.assertRaisesRegex(ValueError, "Invalid TM Transfer Frame Version Number"):
      TmTransferFrame(frame_bytes, False)
  
  def test_sync_flags_validation(self):
    # Sync=0, PktOrder=1 -> Invalid
    hdr_part1 = 0
    hdr_part2_invalid_po = (0 << 14) | (1 << 13) | (3 << 11) # Sync=0, PktOrder=1, SLID=NoSeg
    frame_bytes_invalid_po = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2_invalid_po)
    with self.assertRaisesRegex(ValueError, "Packet Order Flag must be 0 if Synchronisation Flag is 0"):
        TmTransferFrame(frame_bytes_invalid_po, False)

    # Sync=0, SegLenID != 3 -> Invalid
    hdr_part2_invalid_slid = (0 << 14) | (0 << 13) | (0 << 11) # Sync=0, PktOrder=0, SLID=Continuation
    frame_bytes_invalid_slid = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2_invalid_slid)
    with self.assertRaisesRegex(ValueError, "Segment Length Identifier must be 3 .* if Synchronisation Flag is 0"):
        TmTransferFrame(frame_bytes_invalid_slid, False)

  def test_get_secondary_header_copy_not_present(self):
    hdr_part1 = 0; hdr_part2 = 0 # No SH
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2)
    tm_frame = TmTransferFrame(frame_bytes, False)
    self.assertFalse(tm_frame.secondary_header_present)
    with self.assertRaises(IllegalStateException):
        tm_frame.get_secondary_header_copy()

  def test_get_fecf_not_present(self):
    hdr_part1 = 0; hdr_part2 = 0
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2)
    tm_frame = TmTransferFrame(frame_bytes, fecf_present=False)
    self.assertFalse(tm_frame.is_fecf_present())
    with self.assertRaises(IllegalStateException):
        tm_frame.get_fecf()
        
  def test_get_ocf_copy_not_present(self):
    hdr_part1 = 0 # OCF flag is bit 0, so 0 means not present
    hdr_part2 = 0
    frame_bytes = struct.pack(">HBBH", hdr_part1, 0,0,hdr_part2)
    tm_frame = TmTransferFrame(frame_bytes, False)
    self.assertFalse(tm_frame.ocf_present)
    with self.assertRaises(IllegalStateException):
        tm_frame.get_ocf_copy()

if __name__ == '__main__':
    unittest.main()
