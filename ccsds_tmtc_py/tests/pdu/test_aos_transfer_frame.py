import unittest
import struct
from ccsds_tmtc_py.datalink.pdu.aos_transfer_frame import AosTransferFrame, UserDataType
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException

class TestAosTransferFrame(unittest.TestCase):
  def _construct_aos_header(self, scid=0xAA, vcid=1, vcfc=0x123456, replay=0, vcfc_usage=1, vcfc_cycle=0, fhec=False, insert_zone_len=0, user_data_type=UserDataType.M_PDU, ocf=False, fhp_bdp=0):
    hdr1 = (1 << 14) | (scid << 6) | vcid # TFVN=1
    signal_field = (replay << 7) | (vcfc_usage << 6) | vcfc_cycle
    
    header_bytes_list = list(struct.pack(">H", hdr1))
    # Pack VCF count as 3 bytes (from a 4-byte big-endian integer, take last 3)
    header_bytes_list.extend(struct.pack(">I", vcfc)[1:]) 
    header_bytes_list.append(signal_field)
    
    header_bytes = bytearray(header_bytes_list)
        
    if fhec: header_bytes.extend(b'\x00\x00') # Placeholder FHEC
    if insert_zone_len > 0: header_bytes.extend(bytes(insert_zone_len))
        
    if user_data_type == UserDataType.M_PDU or user_data_type == UserDataType.B_PDU:
        header_bytes.extend(struct.pack(">H", fhp_bdp))
    return bytes(header_bytes)

  def test_construct_m_pdu(self):
    fhp = AosTransferFrame.AOS_M_PDU_FIRST_HEADER_POINTER_NO_PACKET
    header = self._construct_aos_header(user_data_type=UserDataType.M_PDU, fhp_bdp=fhp)
    frame_data_payload = b"test_payload"
    # For AosTransferFrame constructor, security_header_length and security_trailer_length are needed if not 0
    aos_frame = AosTransferFrame(header + frame_data_payload, 
                                 frame_header_error_control_present=False, 
                                 insert_zone_length=0, 
                                 user_data_type=UserDataType.M_PDU, 
                                 ocf_present=False, 
                                 fecf_present=False,
                                 security_header_length=0,
                                 security_trailer_length=0)
    self.assertEqual(aos_frame.transfer_frame_version_number, 1)
    self.assertEqual(aos_frame.user_data_type, UserDataType.M_PDU)
    self.assertEqual(aos_frame.first_header_pointer, fhp)
    self.assertTrue(aos_frame.no_start_packet)
    self.assertEqual(aos_frame.get_data_field_copy(), frame_data_payload)

  def test_construct_b_pdu_all_valid(self):
    bdp = AosTransferFrame.AOS_B_PDU_FIRST_HEADER_POINTER_ALL_DATA
    header = self._construct_aos_header(user_data_type=UserDataType.B_PDU, fhp_bdp=bdp)
    frame_data_payload = b"bitstream"
    aos_frame = AosTransferFrame(header + frame_data_payload, False, 0, UserDataType.B_PDU, False, False, 0, 0)
    self.assertEqual(aos_frame.user_data_type, UserDataType.B_PDU)
    self.assertEqual(aos_frame.bitstream_data_pointer, bdp)
    self.assertTrue(aos_frame.bitstream_all_valid) # Corrected method name
    self.assertEqual(aos_frame.get_data_field_copy(), frame_data_payload)

  def test_idle_vc63(self):
    header = self._construct_aos_header(vcid=63, user_data_type=UserDataType.IDLE)
    # Idle frames might not have FHP/BDP field if UserDataType is IDLE
    # The _construct_aos_header adds FHP/BDP if type is M_PDU/B_PDU.
    # Let's reconstruct header specifically for UserDataType.IDLE
    hdr1_idle = (1 << 14) | (0xAA << 6) | 63 # TFVN=1, SCID=0xAA, VCID=63
    vcfc_idle = 0
    signal_field_idle = 0
    header_idle = bytearray(struct.pack(">H", hdr1_idle))
    header_idle.extend(struct.pack(">I", vcfc_idle)[1:])
    header_idle.append(signal_field_idle)
    
    aos_frame = AosTransferFrame(bytes(header_idle), False, 0, UserDataType.IDLE, False, False, 0, 0)
    self.assertTrue(aos_frame.is_idle_frame())

  def test_with_fhec_insert_zone_ocf_fecf(self):
    # The _construct_aos_header already includes fhec and insert_zone_len in its length
    # The UserDataType.VCA does not add FHP/BDP field, so header is shorter
    header_part = self._construct_aos_header(fhec=True, insert_zone_len=2, ocf=True, user_data_type=UserDataType.VCA)
    user_data = b"vca_data"
    ocf_data = b"\x11\x22\x33\x44"
    fecf_data = b"\xAB\xCD"
    frame_bytes = header_part + user_data + ocf_data + fecf_data
    
    aos_frame = AosTransferFrame(frame_bytes, 
                                 frame_header_error_control_present=True, 
                                 insert_zone_length=2, 
                                 user_data_type=UserDataType.VCA, 
                                 ocf_present=True, 
                                 fecf_present=True,
                                 security_header_length=0,
                                 security_trailer_length=0)
    self.assertTrue(aos_frame.frame_header_error_control_present)
    self.assertEqual(aos_frame.get_fhec(), 0) # Placeholder value from _construct_aos_header
    self.assertEqual(aos_frame.get_insert_zone_copy(), b'\x00\x00') # Insert zone data was b'\x00\x00'
    self.assertTrue(aos_frame.is_ocf_present()) # This is from the constructor arg 'ocf_present'
    self.assertEqual(aos_frame.get_ocf_copy(), ocf_data)
    self.assertTrue(aos_frame.is_fecf_present())
    self.assertEqual(aos_frame.get_fecf(), struct.unpack(">H", fecf_data)[0])
    self.assertEqual(aos_frame.get_data_field_copy(), user_data)

  def test_invalid_tfvn(self):
    hdr1_bad_tfvn = (0 << 14) # TFVN=0 for AOS is bad
    vcfc_val = 0
    signal_field_val = 0
    header_bytes_list = list(struct.pack(">H", hdr1_bad_tfvn))
    header_bytes_list.extend(struct.pack(">I", vcfc_val)[1:]) 
    header_bytes_list.append(signal_field_val)
    # Add dummy FHP for M_PDU to ensure minimum length for parser before TFVN check
    header_bytes_list.extend(b'\x00\x00') 
    
    with self.assertRaisesRegex(ValueError, "Invalid AOS Transfer Frame Version Number"):
        AosTransferFrame(bytes(header_bytes_list), False,0,UserDataType.M_PDU,False,False,0,0)

  def test_get_packet_zone_copy_m_pdu(self):
    fhp = 0x10 # Points 16 bytes into the user data (after FHP field)
    header = self._construct_aos_header(user_data_type=UserDataType.M_PDU, fhp_bdp=fhp)
    # User data = sec_hdr (0) + data_after_fhp
    # Packet Zone = FHP_field + sec_hdr (0) + data_after_fhp
    data_after_fhp = b"packet_data_starts_here"
    full_user_data_field = data_after_fhp # Since no security header
    
    aos_frame = AosTransferFrame(header + full_user_data_field, False, 0, UserDataType.M_PDU, False, False, 0, 0)
    
    # get_packet_zone_copy() should return FHP_field + security_header + data_field_proper
    # Here, FHP_field is struct.pack(">H", fhp)
    # security_header is empty
    # data_field_proper is full_user_data_field
    expected_packet_zone = struct.pack(">H", fhp) + full_user_data_field
    self.assertEqual(aos_frame.get_packet_zone_copy(), expected_packet_zone)

  def test_get_bitstream_data_zone_copy_b_pdu(self):
    bdp = 0x20 
    header = self._construct_aos_header(user_data_type=UserDataType.B_PDU, fhp_bdp=bdp)
    data_after_bdp = b"bitstream_data_content"
    full_user_data_field = data_after_bdp
    
    aos_frame = AosTransferFrame(header + full_user_data_field, False, 0, UserDataType.B_PDU, False, False, 0, 0)
    
    expected_bitstream_zone = struct.pack(">H", bdp) + full_user_data_field
    self.assertEqual(aos_frame.get_bitstream_data_zone_copy(), expected_bitstream_zone)

if __name__ == '__main__':
    unittest.main()
