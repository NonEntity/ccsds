import unittest
import struct
from ccsds_tmtc_py.datalink.builder.aos_transfer_frame_builder import AosTransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.aos_transfer_frame import AosTransferFrame, UserDataType
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException
from ccsds_tmtc_py.transport.builder.space_packet_builder import SpacePacketBuilder # For FHP tests

class TestAosTransferFrameBuilder(unittest.TestCase):
  def test_build_m_pdu_no_opt(self):
    frame_len = 50
    builder = AosTransferFrameBuilder.create(
        length=frame_len, frame_header_error_control_present=False, 
        insert_zone_length=0, user_data_type=UserDataType.M_PDU, 
        ocf_present=False, fecf_present=False
    )
    builder.set_spacecraft_id(0xBB).set_virtual_channel_id(2)
    builder.set_virtual_channel_frame_count(0xABCDEF)
    # FHP will be NO_PACKET
    
    payload = b'M_PDU_Data' * 3 # 30 bytes
    remaining_len = builder.get_free_user_data_length()
    self.assertGreaterEqual(remaining_len, len(payload))
    builder.add_data(payload) # Using generic add_data for simplicity here
    
    aos_frame_pdu = builder.build()
    
    reparsed = AosTransferFrame(aos_frame_pdu.get_frame(), False, 0, UserDataType.M_PDU, False, False, 0, 0)
    self.assertEqual(reparsed.spacecraft_id, 0xBB)
    self.assertEqual(reparsed.virtual_channel_id, 2)
    self.assertEqual(reparsed.virtual_channel_frame_count, 0xABCDEF)
    self.assertEqual(reparsed.user_data_type, UserDataType.M_PDU)
    self.assertEqual(reparsed.first_header_pointer, AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET)
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_build_b_pdu_with_fhec_iz_ocf_fecf(self):
    iz_data = b"\x01\x02"
    ocf_data = b"\x11\x22\x33\x44"
    payload = b'B_PDU_Data' * 2 # 20 bytes
    
    # Calculate frame length
    fhec_len = 2
    iz_len = len(iz_data)
    bdp_field_len = 2
    ocf_len = 4
    fecf_len = 2
    frame_len = AosTransferFrame.AOS_PRIMARY_HEADER_LENGTH + fhec_len + iz_len + bdp_field_len + len(payload) + ocf_len + fecf_len

    builder = AosTransferFrameBuilder.create(
        length=frame_len, frame_header_error_control_present=True, 
        insert_zone_length=iz_len, user_data_type=UserDataType.B_PDU, 
        ocf_present=True, fecf_present=True
    )
    builder.set_insert_zone(iz_data).set_ocf(ocf_data)
    builder.set_spacecraft_id(0xCC).set_virtual_channel_id(3).set_virtual_channel_frame_count(0)
    
    # BDP will be default (0) if not set or determined otherwise
    builder.add_data(payload) # Using generic add_data
    
    aos_frame_pdu = builder.build()
    reparsed = AosTransferFrame(aos_frame_pdu.get_frame(), True, iz_len, UserDataType.B_PDU, True, True, 0, 0)
    
    self.assertTrue(reparsed.frame_header_error_control_present)
    self.assertEqual(reparsed.get_insert_zone_copy(), iz_data)
    self.assertTrue(reparsed.is_ocf_present()) # From PDU parsing its header bit
    self.assertEqual(reparsed.get_ocf_copy(), ocf_data)
    self.assertTrue(reparsed.is_fecf_present())
    self.assertEqual(reparsed.get_fecf(), 0) # Placeholder CRC
    self.assertEqual(reparsed.user_data_type, UserDataType.B_PDU)
    # self.assertEqual(reparsed.bitstream_data_pointer, 0) # Default BDP if not set by builder logic
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_build_vca_idle(self):
    frame_len = 20 # Short frame for idle
    builder = AosTransferFrameBuilder.create(
        length=frame_len, frame_header_error_control_present=False,
        insert_zone_length=0, user_data_type=UserDataType.VCA, # VCA does not have FHP/BDP field
        ocf_present=False, fecf_present=False
    )
    builder.set_idle(True) # Sets VCID=63
    
    remaining_len = builder.get_free_user_data_length()
    if remaining_len > 0: builder.add_data(b'\x55' * remaining_len) # Fill with idle pattern
        
    aos_frame_pdu = builder.build()
    reparsed = AosTransferFrame(aos_frame_pdu.get_frame(), False, 0, UserDataType.VCA, False, False, 0, 0)
    
    self.assertTrue(reparsed.is_idle_frame()) # Due to VCID=63
    self.assertEqual(reparsed.virtual_channel_id, 0x3F)
    self.assertEqual(reparsed.user_data_type, UserDataType.VCA)

  def test_fhp_calculation_m_pdu(self):
    frame_len = 100
    builder = AosTransferFrameBuilder.create(frame_len, False, 0, UserDataType.M_PDU, False, False)
    sp_builder = SpacePacketBuilder.create()
    sp_payload = b"SpacePacketPayload"
    sp = sp_builder.add_data(sp_payload).build()
    
    builder.add_space_packet(sp.get_packet())
    remaining = builder.get_free_user_data_length()
    if remaining > 0: builder.add_data(b'F' * remaining)
        
    aos_frame_pdu = builder.build()
    reparsed = AosTransferFrame(aos_frame_pdu.get_frame(), False, 0, UserDataType.M_PDU, False, False, 0, 0)
    self.assertEqual(reparsed.first_header_pointer, 0) # Packet is at the start of user data field
    self.assertEqual(reparsed.get_data_field_copy(), sp.get_packet() + (b'F' * remaining))

  def test_security_header_trailer(self):
    sec_hdr = b"SECUREHDR"
    sec_trl = b"SECURETRL"
    payload = b"payload_sec"
    
    # Calculate required frame length
    base_len = AosTransferFrame.AOS_PRIMARY_HEADER_LENGTH + 2 # 2 for FHP/BDP field
    frame_len = base_len + len(sec_hdr) + len(payload) + len(sec_trl)

    builder = AosTransferFrameBuilder.create(frame_len, False, 0, UserDataType.M_PDU, False, False)
    builder.set_security(header=sec_hdr, trailer=sec_trl)
    
    self.assertEqual(builder.get_free_user_data_length(), len(payload))
    builder.add_data(payload)
    self.assertTrue(builder.is_full())
    
    aos_frame_pdu = builder.build()
    reparsed = AosTransferFrame(aos_frame_pdu.get_frame(), False, 0, UserDataType.M_PDU, False, False, len(sec_hdr), len(sec_trl))
    
    self.assertEqual(reparsed.get_data_field_copy(), payload)
    # Further checks for security header/trailer would need direct access or dedicated getters in PDU

  def test_build_not_full_error(self):
    builder = AosTransferFrameBuilder.create(50, False, 0, UserDataType.M_PDU, False, False)
    builder.add_data(b"short_data") # Not full
    with self.assertRaisesRegex(IllegalStateException, "Frame is not full"):
        builder.build()

if __name__ == '__main__':
    unittest.main()
