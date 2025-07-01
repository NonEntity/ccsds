import unittest
import struct
from ccsds_tmtc_py.datalink.builder.tm_transfer_frame_builder import TmTransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.tm_transfer_frame import TmTransferFrame
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException
from ccsds_tmtc_py.transport.builder.space_packet_builder import SpacePacketBuilder # For FHP tests

class TestTmTransferFrameBuilder(unittest.TestCase):
  def test_build_basic_tm_frame_no_opt_fields(self):
    builder = TmTransferFrameBuilder.create(length=20, sec_header_length=0, ocf_present=False, fecf_present=False)
    builder.set_spacecraft_id(0xAB).set_virtual_channel_id(3)
    builder.set_master_channel_frame_count(100).set_virtual_channel_frame_count(200)
    builder.set_synchronisation_flag(False).set_packet_order_flag(False).set_segment_length_identifier(3)
    # FHP will be NO_PACKET if no packets added
    remaining_len = builder.get_free_user_data_length()
    builder.add_data(b'A' * remaining_len)
    self.assertTrue(builder.is_full())
    tm_frame_pdu = builder.build()
    
    # Re-parse and verify
    reparsed_frame = TmTransferFrame(tm_frame_pdu.get_frame(), fecf_present=False, security_header_length=0, security_trailer_length=0)
    self.assertEqual(reparsed_frame.spacecraft_id, 0xAB)
    self.assertEqual(reparsed_frame.virtual_channel_id, 3)
    self.assertEqual(reparsed_frame.master_channel_frame_count, 100)
    self.assertEqual(reparsed_frame.virtual_channel_frame_count, 200)
    self.assertFalse(reparsed_frame.secondary_header_present)
    self.assertFalse(reparsed_frame.ocf_present) # This is from frame header bit
    self.assertFalse(reparsed_frame.is_fecf_present())
    self.assertEqual(reparsed_frame.first_header_pointer, TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET)
    self.assertEqual(reparsed_frame.get_data_field_copy(), b'A' * remaining_len)

  def test_build_with_sh_ocf_fecf(self):
    sh_data = b"\x01\x02"
    ocf_data = b"\x1A\x2B\x3C\x4D"
    data_payload = b'B' * 10 # Example payload
    
    frame_len = TmTransferFrame.TM_PRIMARY_HEADER_LENGTH + (1 + len(sh_data)) + len(data_payload) + len(ocf_data) + 2 # 2 for FECF
    
    builder = TmTransferFrameBuilder.create(length=frame_len, sec_header_length=len(sh_data), ocf_present=True, fecf_present=True)
    builder.set_secondary_header(sh_data).set_ocf(ocf_data)
    # Set other required fields
    builder.set_spacecraft_id(1).set_virtual_channel_id(1).set_master_channel_frame_count(1).set_virtual_channel_frame_count(1)

    remaining_len = builder.get_free_user_data_length()
    self.assertEqual(remaining_len, len(data_payload)) # Should match our calculation
    builder.add_data(data_payload)
    self.assertTrue(builder.is_full())
    tm_frame_pdu = builder.build()

    reparsed_frame = TmTransferFrame(tm_frame_pdu.get_frame(), fecf_present=True, security_header_length=0, security_trailer_length=0)
    self.assertTrue(reparsed_frame.secondary_header_present)
    self.assertEqual(reparsed_frame.get_secondary_header_copy(), sh_data)
    self.assertTrue(reparsed_frame.ocf_present) # from frame header bit
    self.assertEqual(reparsed_frame.get_ocf_copy(), ocf_data)
    self.assertTrue(reparsed_frame.is_fecf_present())
    self.assertEqual(reparsed_frame.get_fecf(), 0) # Placeholder CRC is 0

  def test_idle_frame_build(self):
    builder = TmTransferFrameBuilder.create(length=10, sec_header_length=0, ocf_present=False, fecf_present=False)
    builder.set_idle(True) # Sets FHP to IDLE
    # Fill remaining data, though for idle it's often pattern
    remaining_len = builder.get_free_user_data_length()
    if remaining_len > 0: builder.add_data(b'\x55' * remaining_len)
    
    tm_frame_pdu = builder.build()
    reparsed_frame = TmTransferFrame(tm_frame_pdu.get_frame(), False,0,0)
    self.assertTrue(reparsed_frame.is_idle_frame())
    self.assertEqual(reparsed_frame.first_header_pointer, TmTransferFrame.TM_FIRST_HEADER_POINTER_IDLE)

  def test_fhp_logic_with_space_packet(self):
    builder = TmTransferFrameBuilder.create(length=100, sec_header_length=0, ocf_present=False, fecf_present=False)
    sp_builder = SpacePacketBuilder.create()
    sp_payload = b"sp_payload"
    sp = sp_builder.add_data(sp_payload).build()
    
    builder.add_space_packet(sp.get_packet())
    # Fill remaining
    remaining_len = builder.get_free_user_data_length()
    if remaining_len > 0: builder.add_data(b'C' * remaining_len)
        
    tm_frame_pdu = builder.build()
    reparsed_frame = TmTransferFrame(tm_frame_pdu.get_frame(), False,0,0)
    self.assertEqual(reparsed_frame.first_header_pointer, 0) # FHP should point to start of SP
    # Verify data field contains the packet + fill data
    expected_data = sp.get_packet() + (b'C' * remaining_len)
    self.assertEqual(reparsed_frame.get_data_field_copy(), expected_data)

  def test_build_not_full_error(self):
    builder = TmTransferFrameBuilder.create(length=20, sec_header_length=0, ocf_present=False, fecf_present=False)
    builder.add_data(b"short") # Not full
    with self.assertRaisesRegex(IllegalStateException, "Frame is not full"):
        builder.build()

  def test_missing_configured_sh_error(self):
    builder = TmTransferFrameBuilder.create(length=20, sec_header_length=2, ocf_present=False, fecf_present=False)
    # SH configured (len 2) but not provided via set_secondary_header()
    builder.add_data(b'A' * builder.get_free_user_data_length()) # Fill data
    with self.assertRaisesRegex(IllegalStateException, "Secondary header was configured but not provided"):
        builder.build()

  def test_missing_configured_ocf_error(self):
    builder = TmTransferFrameBuilder.create(length=20, sec_header_length=0, ocf_present=True, fecf_present=False)
    # OCF configured but not provided via set_ocf()
    builder.add_data(b'A' * builder.get_free_user_data_length()) # Fill data
    with self.assertRaisesRegex(IllegalStateException, "OCF was configured but not provided"):
        builder.build()

  def test_security_header_trailer(self):
    sec_hdr = b"SECHDR"
    sec_trl = b"TRL"
    payload = b"payload_data"
    frame_len = TmTransferFrame.TM_PRIMARY_HEADER_LENGTH + len(sec_hdr) + len(payload) + len(sec_trl)
    
    builder = TmTransferFrameBuilder.create(length=frame_len, sec_header_length=0, ocf_present=False, fecf_present=False)
    builder.set_security(header=sec_hdr, trailer=sec_trl)
    
    self.assertEqual(builder.get_free_user_data_length(), len(payload))
    builder.add_data(payload)
    self.assertTrue(builder.is_full())
    
    tm_frame_pdu = builder.build()
    reparsed_frame = TmTransferFrame(tm_frame_pdu.get_frame(), False, len(sec_hdr), len(sec_trl))
    
    self.assertEqual(reparsed_frame.get_data_field_copy(), payload) # Data field in PDU is between sec hdr/trl
    # To verify security parts, one would need to access them from raw frame or dedicated getters if added
    # For now, check data field integrity.
    # The TmTransferFrame PDU needs to be aware of these for proper data field parsing.
    # TmTransferFrame constructor was updated to accept security_header_length, security_trailer_length.
    
    # Test FHP with security header
    builder.clear_user_data() # Clears payload and resets free_user_data_length considering security
    builder.set_security(header=sec_hdr, trailer=sec_trl) # Re-set security
    
    sp_builder = SpacePacketBuilder.create()
    sp = sp_builder.add_data(b"SP").build()
    
    # Free length should be total_user_data_len - sec_hdr_len - sec_trl_len
    # add_space_packet will add to the space between sec_hdr and sec_trl
    builder.add_space_packet(sp.get_packet())
    
    tm_frame_pdu_sec_fhp = builder.build()
    reparsed_frame_sec_fhp = TmTransferFrame(tm_frame_pdu_sec_fhp.get_frame(), False, len(sec_hdr), len(sec_trl))
    # FHP points to start of SP, relative to start of User Data Field (which is after sec_hdr)
    self.assertEqual(reparsed_frame_sec_fhp.first_header_pointer, 0) 


if __name__ == '__main__':
    unittest.main()
