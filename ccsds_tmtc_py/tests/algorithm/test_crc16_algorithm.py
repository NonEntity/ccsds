import unittest
from ccsds_tmtc_py.algorithm.crc16_algorithm import Crc16Algorithm

class TestCrc16Algorithm(unittest.TestCase):
  def test_ccitt_false_known_values(self):
    self.assertEqual(Crc16Algorithm.calculate(b"123456789"), 0x29B1)
    self.assertEqual(Crc16Algorithm.calculate(b""), Crc16Algorithm.CRC16_INITIAL_VALUE) # Empty data
    data_all_zeros = b'\x00' * 10
    # For 0xFFFF init and 0x1021 poly, 10 zero bytes: 0x706E
    # (Verified with https://crccalc.com/ - Input type HEX, data "00000000000000000000", CRC-16/XMODEM but change init to FFFF)
    # Or more directly: CRC-16/CCITT-FALSE for "00000000000000000000" (hex) -> 0x706e
    self.assertEqual(Crc16Algorithm.calculate(data_all_zeros), 0x706E)

  def test_get_crc16_helper(self):
    data = b"prefix_123456789_suffix"
    self.assertEqual(Crc16Algorithm.get_crc16(data, 7, 9), 0x29B1) # Test "123456789"
    
    # Test with offset and default length (to end of string)
    data2 = b"test_crc_string"
    expected_crc_data2_suffix = Crc16Algorithm.calculate(b"crc_string")
    self.assertEqual(Crc16Algorithm.get_crc16(data2, 5), expected_crc_data2_suffix)

    # Test invalid args
    with self.assertRaises(ValueError):
        Crc16Algorithm.get_crc16(data, -1, 5) # Negative offset
    with self.assertRaises(ValueError):
        Crc16Algorithm.get_crc16(data, 0, len(data) + 1) # Length too long
    with self.assertRaises(ValueError):
        Crc16Algorithm.get_crc16(data, len(data) + 1, 0) # Offset out of bounds

if __name__ == '__main__':
    unittest.main()
