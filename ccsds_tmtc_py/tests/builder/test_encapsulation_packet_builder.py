import unittest
import struct
from ccsds_tmtc_py.transport.builder.encapsulation_packet_builder import EncapsulationPacketBuilder
from ccsds_tmtc_py.transport.pdu.encapsulation_packet import EncapsulationPacket, EncapsulationProtocolIdType

class TestEncapsulationPacketBuilder(unittest.TestCase):
  def test_build_idle_packet(self):
    builder = EncapsulationPacketBuilder.create().set_idle()
    ep_pdu = builder.build()
    
    reparsed = EncapsulationPacket(ep_pdu.get_packet())
    self.assertTrue(reparsed.is_idle())
    self.assertEqual(reparsed.primary_header_length, 1)
    self.assertEqual(reparsed.get_length(), 1)
    self.assertEqual(reparsed.encapsulation_protocol_id, EncapsulationProtocolIdType.PROTOCOL_ID_IDLE)

  def test_build_fixed_lol_2_byte_header(self):
    builder = EncapsulationPacketBuilder.create()
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_LTP)
    payload = b"LTP_data"
    builder.set_data(payload)
    builder.set_length_of_length_code(1) # Force PHL=2 bytes
    
    ep_pdu = builder.build()
    reparsed = EncapsulationPacket(ep_pdu.get_packet())
    
    self.assertEqual(reparsed.primary_header_length, 2)
    self.assertEqual(reparsed.get_length(), 2 + len(payload))
    self.assertEqual(reparsed.get_data_field_copy(), payload)
    self.assertFalse(reparsed.user_defined_field_present) # Not set

  def test_build_fixed_lol_4_byte_header_with_optional(self):
    builder = EncapsulationPacketBuilder.create()
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC)
    builder.set_user_defined_field(0xA)
    builder.set_encapsulation_protocol_id_extension(0x5)
    payload = b"Mission_data_payload"
    builder.set_data(payload)
    builder.set_length_of_length_code(2) # Force PHL=4 bytes

    ep_pdu = builder.build()
    reparsed = EncapsulationPacket(ep_pdu.get_packet())

    self.assertEqual(reparsed.primary_header_length, 4)
    self.assertTrue(reparsed.user_defined_field_present)
    self.assertEqual(reparsed.user_defined_field, 0xA)
    self.assertTrue(reparsed.encapsulation_protocol_id_extension_present)
    self.assertEqual(reparsed.encapsulation_protocol_id_extension, 0x5)
    self.assertFalse(reparsed.ccsds_defined_field_present) # Not set
    self.assertEqual(reparsed.get_length(), 4 + len(payload))
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_build_fixed_lol_8_byte_header_all_fields(self):
    builder = EncapsulationPacketBuilder.create()
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_RESERVED_2)
    builder.set_user_defined_field(0x3)
    builder.set_encapsulation_protocol_id_extension(0x7)
    builder.set_ccsds_defined_field(b"\xAB\xCD")
    payload = b"Data_for_8_byte_header"
    builder.set_data(payload)
    builder.set_length_of_length_code(3) # Force PHL=8 bytes

    ep_pdu = builder.build()
    reparsed = EncapsulationPacket(ep_pdu.get_packet())

    self.assertEqual(reparsed.primary_header_length, 8)
    self.assertTrue(reparsed.user_defined_field_present)
    self.assertEqual(reparsed.user_defined_field, 0x3)
    self.assertTrue(reparsed.encapsulation_protocol_id_extension_present)
    self.assertEqual(reparsed.encapsulation_protocol_id_extension, 0x7)
    self.assertTrue(reparsed.ccsds_defined_field_present)
    self.assertEqual(reparsed.ccsds_defined_field, b"\xAB\xCD")
    self.assertEqual(reparsed.get_length(), 8 + len(payload))
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_dynamic_lol_selection(self):
    builder = EncapsulationPacketBuilder.create()
    # Small payload, no optional fields -> should select PHL=2
    payload1 = b"small"
    builder.set_data(payload1)
    ep1 = builder.build()
    self.assertEqual(EncapsulationPacket(ep1.get_packet()).primary_header_length, 2)

    # Payload > 253 (255 - 2 for PHL), no optional fields -> should select PHL=4
    builder.clear_data()
    payload2 = b'A' * 260 
    builder.set_data(payload2)
    ep2 = builder.build()
    reparsed2 = EncapsulationPacket(ep2.get_packet())
    self.assertEqual(reparsed2.primary_header_length, 4, f"PHL for payload size {len(payload2)} was {reparsed2.primary_header_length}, expected 4")


    # With UserDef/ExtID, payload > 251 (255-4) -> should select PHL=4
    builder.clear_data()
    builder.set_user_defined_field(1) # This makes PHL at least 4
    payload3 = b'B' * 10
    builder.set_data(payload3)
    ep3 = builder.build()
    self.assertEqual(EncapsulationPacket(ep3.get_packet()).primary_header_length, 4)


    # With CCSDSDef field -> should select PHL=8
    builder.clear_data()
    builder.set_ccsds_defined_field(b"\x01\x02") # This makes PHL 8
    payload4 = b'C' * 10
    builder.set_data(payload4)
    ep4 = builder.build()
    self.assertEqual(EncapsulationPacket(ep4.get_packet()).primary_header_length, 8)

  def test_create_from_existing_packet(self):
    builder_orig = EncapsulationPacketBuilder.create()
    builder_orig.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC)
    builder_orig.set_user_defined_field(0xE)
    builder_orig.set_data(b"CopyTest")
    builder_orig.set_length_of_length_code(2) # PHL=4
    ep_orig = builder_orig.build()

    # Create new builder from ep_orig, copying data
    builder_copy = EncapsulationPacketBuilder.create(initialiser=ep_orig, copy_data_field=True)
    ep_copy = builder_copy.build()
    self.assertEqual(ep_copy.get_packet(), ep_orig.get_packet())
    self.assertEqual(EncapsulationPacket(ep_copy.get_packet()).user_defined_field, 0xE)

    # Create new builder, not copying data
    builder_no_data_copy = EncapsulationPacketBuilder.create(initialiser=ep_orig, copy_data_field=False)
    ep_no_data = builder_no_data_copy.build() # Builder has fields, but no payload
    reparsed_no_data = EncapsulationPacket(ep_no_data.get_packet())
    self.assertEqual(reparsed_no_data.user_defined_field, 0xE) # Header fields copied
    self.assertEqual(reparsed_no_data.encapsulated_data_field_length, 0) # Data not copied


if __name__ == '__main__':
    unittest.main()
