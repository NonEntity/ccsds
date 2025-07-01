import unittest
import struct
from ccsds_tmtc_py.transport.pdu.space_packet import SpacePacket
from ccsds_tmtc_py.transport.pdu.common import SequenceFlagType

class TestSpacePacket(unittest.TestCase):
  def test_construct_and_parse_tm_header(self):
    # Version=0, Type=TM (0), SH=present (1), APID=0x123, SeqFlags=UNSEGMENTED (3), PSC=50, DataLength=len(data)-1
    user_data = b"\x01\x02\x03\x04"
    packet_data_len_field = len(user_data) - 1
    hdr_part1 = (SpacePacket.SP_VERSION << 13) | (0 << 12) | (1 << 11) | 0x123
    hdr_part2 = (SequenceFlagType.UNSEGMENTED.value << 14) | 50
    packet_bytes = struct.pack(">HHH", hdr_part1, hdr_part2, packet_data_len_field) + user_data
    sp = SpacePacket(packet_bytes, quality_indicator=True)
    self.assertEqual(sp.get_version(), 0) # Use getter method
    self.assertTrue(sp.is_telemetry_packet)
    self.assertTrue(sp.secondary_header_flag)
    self.assertEqual(sp.apid, 0x123)
    self.assertEqual(sp.sequence_flag, SequenceFlagType.UNSEGMENTED)
    self.assertEqual(sp.packet_sequence_count, 50)
    self.assertEqual(sp.ccsds_defined_data_length, packet_data_len_field)
    self.assertEqual(sp.user_data_length, len(user_data))
    self.assertTrue(sp.quality_indicator)
    self.assertFalse(sp.is_idle())
    self.assertEqual(sp.get_data_field_copy(), user_data)

  def test_telecommand_packet(self):
    # Min length for header: primary header (6 bytes) + user data (0 bytes, so length field is 0xFFFF)
    hdr_part1 = (SpacePacket.SP_VERSION << 13) | (1 << 12) # Type=TC (1)
    packet_bytes = struct.pack(">HHH", hdr_part1, 0, 0xFFFF) 
    sp = SpacePacket(packet_bytes)
    self.assertFalse(sp.is_telemetry_packet)

  def test_sequence_flags(self):
    for sf_enum in SequenceFlagType:
      hdr_part2 = (sf_enum.value << 14)
      # Min length for header: primary header (6 bytes) + user data (0 bytes, so length field is 0xFFFF)
      packet_bytes = struct.pack(">HHH", 0, hdr_part2, 0xFFFF)
      sp = SpacePacket(packet_bytes)
      self.assertEqual(sp.sequence_flag, sf_enum)

  def test_idle_packet(self):
    hdr_part1 = SpacePacket.SP_IDLE_APID_VALUE
    # Min length for header: primary header (6 bytes) + user data (0 bytes, so length field is 0xFFFF)
    packet_bytes = struct.pack(">HHH", hdr_part1,0,0xFFFF)
    sp = SpacePacket(packet_bytes)
    self.assertTrue(sp.is_idle())

  def test_invalid_length(self):
    user_data = b"abc" # 3 bytes
    # Packet Data Length field should be (len(user_data) - 1) = 2
    # Let's set it to 1 (which means user_data should be 2 bytes long)
    packet_data_len_field = len(user_data) - 2 
    packet_bytes = struct.pack(">HHH", 0,0,packet_data_len_field) + user_data
    with self.assertRaisesRegex(ValueError, "Actual packet length .* does not match expected length"):
        SpacePacket(packet_bytes)

  def test_invalid_version(self):
    hdr_part1 = (1 << 13) # Invalid version (should be SpacePacket.SP_VERSION which is 0)
    # Min length for header: primary header (6 bytes) + user data (0 bytes, so length field is 0xFFFF)
    packet_bytes = struct.pack(">HHH", hdr_part1,0,0xFFFF)
    with self.assertRaisesRegex(ValueError, "Invalid Space Packet Version"):
        SpacePacket(packet_bytes)

  def test_packet_too_short(self):
    # Frame shorter than primary header length
    short_frame = b"\x00\x00\x00\x00" # 4 bytes, SP_PRIMARY_HEADER_LENGTH is 6
    with self.assertRaisesRegex(ValueError, "Packet data too short for Space Packet Primary Header"):
        SpacePacket(short_frame)

if __name__ == '__main__':
    unittest.main()
