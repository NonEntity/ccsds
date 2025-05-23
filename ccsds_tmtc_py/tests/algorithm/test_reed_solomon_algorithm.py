import unittest
from ccsds_tmtc_py.algorithm.reed_solomon_algorithm import ReedSolomonAlgorithm
import random # For error generation
# import reedsolo # Not strictly needed for test file unless directly accessing reedsolo.ReedSolomonError

class TestReedSolomonAlgorithm(unittest.TestCase):
  def test_tm_255_223_encode_decode_no_errors(self):
    rs = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    data = bytes([random.randint(0, 255) for _ in range(rs.k)])
    codeword = rs.encode(data)
    self.assertEqual(len(codeword), rs.n, "Codeword length should be N")
    self.assertEqual(codeword[:rs.k], data, "First K bytes of codeword should be original data")
    
    decoded_data = rs.decode(codeword)
    self.assertEqual(len(decoded_data), rs.k, "Decoded data length should be K")
    self.assertEqual(data, decoded_data, "Decoded data should match original data")

  def test_tm_255_223_correctable_errors(self):
    rs = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    data = bytes([random.randint(0, 255) for _ in range(rs.k)])
    codeword = bytearray(rs.encode(data)) # bytearray to allow modification
    
    num_errors = rs.nsym // 2 # Max correctable errors
    if num_errors == 0: # Should not happen for (255,223) where nsym=32
        self.skipTest("RS code cannot correct any errors (nsym/2 is 0)")
        return

    # Introduce errors
    error_positions = random.sample(range(rs.n), num_errors)
    for pos in error_positions:
      codeword[pos] = (codeword[pos] + random.randint(1, 255)) & 0xFF # Flip some bits by adding
        
    try:
      decoded_data = rs.decode(bytes(codeword))
      self.assertEqual(data, decoded_data, f"Should correct {num_errors} errors")
    except ValueError as e:
      # This might happen if the error pattern, by chance, creates another valid codeword
      # or if the library has limitations. For a robust test, specific error patterns might be better.
      self.fail(f"RS decode failed for {num_errors} errors: {e}")

  def test_tm_255_223_uncorrectable_errors(self):
    rs = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    data = bytes([random.randint(0, 255) for _ in range(rs.k)])
    codeword = bytearray(rs.encode(data))
    
    num_errors = (rs.nsym // 2) + 1
    if num_errors > rs.n: # Ensure we don't try to make more errors than positions available
        num_errors = rs.n 
        if num_errors <= rs.nsym // 2 : # Check if code can correct this many errors
             self.skipTest(f"Cannot introduce more than {rs.nsym // 2} errors distinct from correctable for this N,K.")
             return

    error_positions = random.sample(range(rs.n), num_errors)
    for pos in error_positions:
      codeword[pos] = (codeword[pos] + random.randint(1, 255)) & 0xFF
        
    # The reedsolo library raises reedsolo.ReedSolomonError, which our wrapper catches and re-raises as ValueError
    with self.assertRaisesRegex(ValueError, "Uncorrectable error|Could not locate error|too many errors"): 
      rs.decode(bytes(codeword))

  def test_input_length_validation(self):
    rs = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    with self.assertRaisesRegex(ValueError, "Input data length .* for encode does not match K"):
        rs.encode(bytes(rs.k - 1))
    with self.assertRaisesRegex(ValueError, "Codeword length .* for decode does not match N"):
        rs.decode(bytes(rs.n - 1))
    
    with self.assertRaisesRegex(ValueError, "Input data length .* for encode does not match K"):
        rs.encode(bytes(rs.k + 1))
    with self.assertRaisesRegex(ValueError, "Codeword length .* for decode does not match N"):
        rs.decode(bytes(rs.n + 1))

if __name__ == '__main__':
    unittest.main()
    # Note: The AOS FHEC (10,6) comments from the prompt are related to future work
    # and not implemented as a test here due to reedsolo's byte-orientation (c_exp=8).
