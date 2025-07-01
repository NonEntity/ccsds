import unittest
from ccsds_tmtc_py.algorithm.bch_cltu_algorithm import BchCltuAlgorithm

class TestBchCltuAlgorithm(unittest.TestCase):
  def test_cltu_pseudo_bch_encode_decode_placeholder(self):
    # This tests the placeholder sum-based checksum.
    data_block = b"\x01\x02\x03\x04\x05\x06\x07"
    coded_block = BchCltuAlgorithm.encode_cltu_block(data_block)
    self.assertEqual(len(coded_block), 8)
    expected_checksum = sum(data_block) & 0xFF
    self.assertEqual(coded_block[7], expected_checksum)
    
    decoded_block = BchCltuAlgorithm.decode_cltu_block(coded_block)
    self.assertEqual(decoded_block, data_block)

  def test_cltu_pseudo_bch_decode_error_placeholder(self):
    data_block = b"\x10\x20\x30\x40\x50\x60\x70"
    coded_block_valid = BchCltuAlgorithm.encode_cltu_block(data_block)
    corrupted_coded_block = bytearray(coded_block_valid)
    corrupted_coded_block[7] ^= 0xFF # Corrupt checksum byte
    with self.assertRaisesRegex(ValueError, "CLTU block checksum error"): # Match error from placeholder
        BchCltuAlgorithm.decode_cltu_block(bytes(corrupted_coded_block))
        
  def test_invalid_lengths(self):
    with self.assertRaisesRegex(ValueError, "CLTU data block for pseudo-BCH encoding must be 7 bytes"):
        BchCltuAlgorithm.encode_cltu_block(b"123456") # Too short
    with self.assertRaisesRegex(ValueError, "CLTU data block for pseudo-BCH encoding must be 7 bytes"):
        BchCltuAlgorithm.encode_cltu_block(b"12345678") # Too long
        
    with self.assertRaisesRegex(ValueError, "CLTU coded block for pseudo-BCH decoding must be 8 bytes"):
        BchCltuAlgorithm.decode_cltu_block(b"1234567") # Too short
    with self.assertRaisesRegex(ValueError, "CLTU coded block for pseudo-BCH decoding must be 8 bytes"):
        BchCltuAlgorithm.decode_cltu_block(b"123456789") # Too long

if __name__ == '__main__':
    unittest.main()
