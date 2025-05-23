import unittest
from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm

class TestRandomizerAlgorithm(unittest.TestCase):
  def test_tm_randomization_properties(self):
    original_data = bytearray(b"Hello CCSDS TM Randomization Test!")
    data_copy1 = original_data[:]
    RandomizerAlgorithm.randomize_frame_tm(data_copy1)
    self.assertNotEqual(original_data, data_copy1, "Randomized data should differ from original.")
    
    data_copy2 = data_copy1[:]
    RandomizerAlgorithm.randomize_frame_tm(data_copy2) # Apply again
    self.assertEqual(original_data, data_copy2, "Applying TM randomization twice should yield original data.")

  def test_cltu_randomization_properties(self):
    original_data = bytearray(b"CLTU Block Randomization Test Data 123.")
    data_copy1 = original_data[:]
    RandomizerAlgorithm.randomize_cltu(data_copy1, 0, len(data_copy1))
    self.assertNotEqual(original_data, data_copy1)
    
    data_copy2 = data_copy1[:]
    RandomizerAlgorithm.randomize_cltu(data_copy2, 0, len(data_copy2))
    self.assertEqual(original_data, data_copy2, "Applying CLTU randomization twice should yield original.")

  def test_cltu_randomization_slice(self):
    prefix = b"PREFIX--"
    target = bytearray(b"TARGETDATA")
    suffix = b"--SUFFIX"
    original_target_copy = target[:]
    full_data = bytearray(prefix + target + suffix)
    RandomizerAlgorithm.randomize_cltu(full_data, len(prefix), len(prefix) + len(target))
    
    self.assertEqual(full_data[:len(prefix)], prefix, "Prefix should remain unchanged.")
    self.assertEqual(full_data[len(prefix)+len(target):], suffix, "Suffix should remain unchanged.")
    self.assertNotEqual(full_data[len(prefix):len(prefix)+len(target)], original_target_copy, "Target slice should be randomized.")
    
    RandomizerAlgorithm.randomize_cltu(full_data, len(prefix), len(prefix) + len(target)) # Apply again to slice
    self.assertEqual(full_data[len(prefix):len(prefix)+len(target)], original_target_copy, "Double randomized slice should be original.")

if __name__ == '__main__':
    unittest.main()
