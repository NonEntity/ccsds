import unittest
import struct
from ccsds_tmtc_py.transport.builder.space_packet_builder import SpacePacketBuilder
from ccsds_tmtc_py.transport.pdu.space_packet import SpacePacket
from ccsds_tmtc_py.transport.pdu.common import SequenceFlagType

class TestSpacePacketBuilder(unittest.TestCase):
  def test_build_basic_tm_packet(self):
    builder = SpacePacketBuilder.create()
    builder.set_apid(0x123).set_packet_sequence_count(50).set_telemetry_packet()
    payload = b"\xDE\xAD\xBE\xEF"
    bytes_not_written = builder.add_data(payload)
    self.assertEqual(bytes_not_written, 0)
    sp_pdu = builder.build()

    reparsed_sp = SpacePacket(sp_pdu.get_packet())
    self.assertEqual(reparsed_sp.apid, 0x123)
    self.assertEqual(reparsed_sp.packet_sequence_count, 50)
    self.assertTrue(reparsed_sp.is_telemetry_packet)
    self.assertEqual(reparsed_sp.get_data_field_copy(), payload)
    self.assertEqual(reparsed_sp.user_data_length, len(payload))
    self.assertEqual(reparsed_sp.ccsds_defined_data_length, len(payload) - 1)
    self.assertFalse(reparsed_sp.secondary_header_flag) # Default
    self.assertEqual(reparsed_sp.sequence_flag, SequenceFlagType.UNSEGMENTED) # Default

  def test_build_telecommand_packet_with_sh(self):
    builder = SpacePacketBuilder.create(quality_indicator=False)
    builder.set_apid(0x456).set_packet_sequence_count(100).set_telecommand_packet()
    builder.set_secondary_header_flag(True)
    payload_tc = b"TC_DATA"
    builder.add_data(payload_tc)
    sp_pdu = builder.build()

    reparsed_sp = SpacePacket(sp_pdu.get_packet())
    self.assertEqual(reparsed_sp.apid, 0x456)
    self.assertEqual(reparsed_sp.packet_sequence_count, 100)
    self.assertFalse(reparsed_sp.is_telemetry_packet)
    self.assertTrue(reparsed_sp.secondary_header_flag)
    self.assertEqual(reparsed_sp.get_data_field_copy(), payload_tc)
    self.assertFalse(reparsed_sp.quality_indicator)

  def test_sequence_flags(self):
    for sf_enum in SequenceFlagType:
        builder = SpacePacketBuilder.create().set_sequence_flag(sf_enum)
        # Build with minimal payload (0 bytes)
        sp_pdu = builder.build()
        reparsed_sp = SpacePacket(sp_pdu.get_packet())
        self.assertEqual(reparsed_sp.sequence_flag, sf_enum)
        self.assertEqual(reparsed_sp.user_data_length, 0)
        self.assertEqual(reparsed_sp.ccsds_defined_data_length, 0xFFFF) # Length - 1 for 0 bytes

  def test_idle_packet(self):
    builder = SpacePacketBuilder.create().set_idle() # Sets APID to idle value
    payload_idle = b"IDLE_PAYLOAD_CAN_EXIST" # Idle packets can have payload
    builder.add_data(payload_idle)
    sp_pdu = builder.build()
    
    reparsed_sp = SpacePacket(sp_pdu.get_packet())
    self.assertTrue(reparsed_sp.is_idle())
    self.assertEqual(reparsed_sp.apid, SpacePacket.SP_IDLE_APID_VALUE)
    self.assertEqual(reparsed_sp.get_data_field_copy(), payload_idle)

  def test_data_handling_add_multiple_clear(self):
    builder = SpacePacketBuilder.create()
    builder.add_data(b"part1")
    builder.add_data(b"part2")
    expected_payload = b"part1part2"
    sp_pdu_parts = builder.build()
    self.assertEqual(SpacePacket(sp_pdu_parts.get_packet()).get_data_field_copy(), expected_payload)

    builder.clear_user_data()
    self.assertEqual(builder.get_free_user_data_length(), SpacePacketBuilder()._max_user_data_length)
    sp_pdu_cleared = builder.build()
    self.assertEqual(SpacePacket(sp_pdu_cleared.get_packet()).user_data_length, 0)

  def test_data_overflow(self):
    builder = SpacePacketBuilder.create()
    max_len = builder._max_user_data_length
    bytes_not_written = builder.add_data(b'A' * (max_len + 10)) # 10 bytes overflow
    self.assertEqual(bytes_not_written, 10)
    self.assertTrue(builder.is_full())
    sp_pdu_full = builder.build()
    self.assertEqual(SpacePacket(sp_pdu_full.get_packet()).user_data_length, max_len)
    
  def test_create_from_existing(self):
    builder1 = SpacePacketBuilder.create().set_apid(0x77).add_data(b"original")
    sp1 = builder1.build()
    
    # Create new builder from sp1, copying data
    builder2 = SpacePacketBuilder.create(initialiser=sp1, copy_data_field=True)
    sp2 = builder2.build()
    self.assertEqual(sp1.get_packet(), sp2.get_packet())

    # Create new builder from sp1, without copying data
    builder3 = SpacePacketBuilder.create(initialiser=sp1, copy_data_field=False)
    sp3 = builder3.build() # Will have header fields from sp1, but no data
    reparsed_sp3 = SpacePacket(sp3.get_packet())
    self.assertEqual(reparsed_sp3.apid, sp1.apid)
    self.assertEqual(reparsed_sp3.user_data_length, 0)

  def test_increment_sequence_count(self):
    builder = SpacePacketBuilder.create().set_packet_sequence_count(0x3FFE)
    builder.increment_packet_sequence_count() # -> 0x3FFF
    builder.increment_packet_sequence_count() # -> 0x0000 (wraps around)
    sp = builder.build()
    self.assertEqual(SpacePacket(sp.get_packet()).packet_sequence_count, 0)

if __name__ == '__main__':
    unittest.main()
