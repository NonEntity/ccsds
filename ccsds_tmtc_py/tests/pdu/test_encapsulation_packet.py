import unittest
import struct
from ccsds_tmtc_py.transport.pdu.encapsulation_packet import EncapsulationPacket, EncapsulationProtocolIdType

class TestEncapsulationPacket(unittest.TestCase):
  def test_construct_idle_packet_phl1(self):
    # Version=7 (111b), ProtoID=IDLE(000b), LenOfLen code=0 (00b -> PHL=1 byte)
    # First octet: 111 000 00 = 0xE0
    idle_pkt_byte = (EncapsulationPacket.EP_VERSION << 5) | \
                    (EncapsulationProtocolIdType.PROTOCOL_ID_IDLE.value << 2) | \
                    0 
    ep = EncapsulationPacket(bytes([idle_pkt_byte]))
    self.assertEqual(ep.get_version(), EncapsulationPacket.EP_VERSION) # Use getter
    self.assertTrue(ep.is_idle())
    self.assertEqual(ep.primary_header_length, 1)
    self.assertEqual(ep.get_length(), 1)
    self.assertEqual(ep.encapsulated_data_field_length, 0)
    self.assertFalse(ep.user_defined_field_present)
    self.assertFalse(ep.encapsulation_protocol_id_extension_present)
    self.assertFalse(ep.ccsds_defined_field_present)

  def test_construct_2_byte_header(self):
    payload = b"datadata" # 8 bytes
    total_len = 2 + len(payload) # PHL=2 + payload_len = 10
    # Version=7, ProtoID=LTP(1), LenOfLen code=1 (PHL=2 bytes)
    # First octet: 111 001 01 = 0xE5
    hdr0 = (EncapsulationPacket.EP_VERSION << 5) | \
           (EncapsulationProtocolIdType.PROTOCOL_ID_LTP.value << 2) | \
           1 
    hdr1 = total_len # Length field is total packet length
    
    ep = EncapsulationPacket(bytes([hdr0, hdr1]) + payload)
    self.assertEqual(ep.primary_header_length, 2)
    self.assertEqual(ep.encapsulation_protocol_id, EncapsulationProtocolIdType.PROTOCOL_ID_LTP)
    self.assertEqual(ep.get_length(), total_len) # total_packet_length is parsed
    self.assertEqual(ep.get_data_field_copy(), payload)
    self.assertFalse(ep.user_defined_field_present)
    self.assertFalse(ep.encapsulation_protocol_id_extension_present)
    self.assertFalse(ep.ccsds_defined_field_present)

  def test_construct_4_byte_header(self):
    payload = b"cfdp_payload_long_enough" # 24 bytes
    total_len = 4 + len(payload) # PHL=4 + payload_len = 28
    user_def = 0xA
    ext_id = 0x5
    # Version=7, ProtoID=MISSION_SPECIFIC(7), LenOfLen code=2 (PHL=4 bytes)
    # First octet: 111 111 10 = 0xFE
    hdr0 = (EncapsulationPacket.EP_VERSION << 5) | \
           (EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC.value << 2) | \
           2
    # Second octet: UserDef (1010b), ExtID (0101b) -> 10100101 = 0xA5
    hdr1 = (user_def << 4) | ext_id
    
    ep_bytes = bytes([hdr0, hdr1]) + struct.pack(">H", total_len) + payload
    ep = EncapsulationPacket(ep_bytes)
    
    self.assertEqual(ep.primary_header_length, 4)
    self.assertEqual(ep.encapsulation_protocol_id, EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC)
    self.assertTrue(ep.user_defined_field_present)
    self.assertEqual(ep.user_defined_field, user_def)
    self.assertTrue(ep.encapsulation_protocol_id_extension_present)
    self.assertEqual(ep.encapsulation_protocol_id_extension, ext_id)
    self.assertFalse(ep.ccsds_defined_field_present)
    self.assertEqual(ep.get_length(), total_len)
    self.assertEqual(ep.get_data_field_copy(), payload)

  def test_construct_8_byte_header(self):
    payload = b"long_payload_for_8_byte_header" # 30 bytes
    total_len = 8 + len(payload) # PHL=8 + payload_len = 38
    user_def = 0x3
    ext_id = 0x7
    ccsds_def = b"\xCA\xFE"
    # Version=7, ProtoID=RESERVED_2(2), LenOfLen code=3 (PHL=8 bytes)
    # First octet: 111 010 11 = 0xEB
    hdr0 = (EncapsulationPacket.EP_VERSION << 5) | \
           (EncapsulationProtocolIdType.PROTOCOL_ID_RESERVED_2.value << 2) | \
           3
    # Second octet: UserDef (0011b), ExtID (0111b) -> 00110111 = 0x37
    hdr1 = (user_def << 4) | ext_id
    
    ep_bytes = bytes([hdr0, hdr1]) + ccsds_def + struct.pack(">I", total_len) + payload
    ep = EncapsulationPacket(ep_bytes)
    
    self.assertEqual(ep.primary_header_length, 8)
    self.assertEqual(ep.encapsulation_protocol_id, EncapsulationProtocolIdType.PROTOCOL_ID_RESERVED_2)
    self.assertTrue(ep.user_defined_field_present)
    self.assertEqual(ep.user_defined_field, user_def)
    self.assertTrue(ep.encapsulation_protocol_id_extension_present)
    self.assertEqual(ep.encapsulation_protocol_id_extension, ext_id)
    self.assertTrue(ep.ccsds_defined_field_present)
    self.assertEqual(ep.ccsds_defined_field, ccsds_def)
    self.assertEqual(ep.get_length(), total_len)
    self.assertEqual(ep.get_data_field_copy(), payload)

  def test_invalid_version(self):
    # Version=6 (110b) -> 110 000 00 = 0xC0
    invalid_version_byte = 0xC0 
    with self.assertRaisesRegex(ValueError, "Invalid Encapsulation Packet Version"):
        EncapsulationPacket(bytes([invalid_version_byte]))

  def test_length_mismatch(self):
    # PHL=2, total_len in header = 10, actual payload makes it 11
    payload = b"data12345" # 9 bytes
    total_len_in_header = 2 + len(payload) -1 # Header says 10
    hdr0 = (EncapsulationPacket.EP_VERSION << 5) | \
           (EncapsulationProtocolIdType.PROTOCOL_ID_LTP.value << 2) | 1
    hdr1 = total_len_in_header
    
    packet_bytes = bytes([hdr0, hdr1]) + payload # Actual total length is 2 + 9 = 11
    with self.assertRaisesRegex(ValueError, "Actual packet length .* does not match total packet length from header"):
        EncapsulationPacket(packet_bytes)

  def test_packet_too_short_for_header(self):
    # PHL=4 indicated by LenOfLen code 2, but packet is only 3 bytes long
    hdr0_phl4 = (EncapsulationPacket.EP_VERSION << 5) | (0 << 2) | 2
    short_packet_bytes = bytes([hdr0_phl4, 0x00, 0x00]) # Only 3 bytes
    with self.assertRaisesRegex(ValueError, "Packet data too short for determined primary header length"):
        EncapsulationPacket(short_packet_bytes)

if __name__ == '__main__':
    unittest.main()
