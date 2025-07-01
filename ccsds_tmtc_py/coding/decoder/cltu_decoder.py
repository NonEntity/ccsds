from ccsds_tmtc_py.algorithm.bch_cltu_algorithm import BchCltuAlgorithm
from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm

class CltuDecoder:
  START_SEQUENCE = b'\xEB\x90'
  # Per CCSDS 231.0-B-3, the Tail Sequence is 8 octets of C5.
  # For robust detection, we might look for a part of it or the whole thing.
  # The Java code uses rindex on the full 8-byte sequence.
  STOP_SEQUENCE = b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5' 
  FILLER_BYTE = 0x55

  def __init__(self, randomize: bool = True):
    self._randomize = randomize

  def apply(self, data: bytes) -> bytes:
    try:
        start_seq_idx = data.index(self.START_SEQUENCE)
    except ValueError:
        raise ValueError("CLTU Start Sequence (EB90) not found")
    
    # Search for the stop sequence from the position after the start sequence
    data_after_start_seq_payload = data[start_seq_idx + len(self.START_SEQUENCE):]
    
    try:
        # rindex finds the last occurrence. This is generally what we want for the tail.
        stop_seq_idx_in_payload = data_after_start_seq_payload.rindex(self.STOP_SEQUENCE)
    except ValueError:
        # If full stop sequence not found, try with a shorter marker as fallback, or error.
        # The prompt used TAIL_SEQUENCE_START_MARKER = b'\xC5\C5\xC5\xC5'
        # For now, strict check for full stop sequence:
        raise ValueError("CLTU Stop Sequence (C5 x8) not found")

    # The actual coded data stream is between the start sequence and the found stop sequence
    coded_data_stream = data_after_start_seq_payload[:stop_seq_idx_in_payload]
    
    if len(coded_data_stream) % 8 != 0:
        raise ValueError(f"CLTU coded data stream length ({len(coded_data_stream)}) is not a multiple of 8 bytes (a whole number of codeblocks).")

    decoded_parts = []
    for i in range(len(coded_data_stream) // 8):
        coded_block = coded_data_stream[i*8 : (i+1)*8]
        
        # BCH decode first. decode_cltu_block returns 7 bytes data or raises error.
        bch_decoded_data = bytearray(BchCltuAlgorithm.decode_cltu_block(coded_block)) # Make it mutable
        
        if self._randomize:
            # Derandomize the 7-byte data part.
            RandomizerAlgorithm.randomize_cltu(bch_decoded_data, 0, 7) # randomize_cltu modifies in-place
            
        decoded_parts.append(bytes(bch_decoded_data))
        
    final_data_with_fillers = b"".join(decoded_parts)
    
    # Remove trailing filler bytes
    # rstrip only removes from the end. If filler bytes are elsewhere, they remain.
    # This is usually the correct behavior for CLTU.
    final_data = final_data_with_fillers.rstrip(bytes([self.FILLER_BYTE]))
    
    return final_data

  def __call__(self, data: bytes) -> bytes:
    return self.apply(data)

if __name__ == '__main__':
    # Test data from CltuEncoder example
    # Non-randomized: START_SEQUENCE + (41041041041040 + F6) + STOP_SEQUENCE
    original_data_nr = bytes.fromhex("41041041041040")
    bch_encoded_nr = BchCltuAlgorithm.encode_cltu_block(original_data_nr)
    cltu_stream_non_randomized = CltuDecoder.START_SEQUENCE + bch_encoded_nr + CltuDecoder.STOP_SEQUENCE
    
    decoder_non_randomized = CltuDecoder(randomize=False)
    decoded_data_nr = decoder_non_randomized.apply(cltu_stream_non_randomized)
    print(f"Decoded (non-randomized): {decoded_data_nr.hex().upper()}")
    assert decoded_data_nr == original_data_nr
    print("Non-randomized decode test PASSED.")

    # Randomized: START + (Randomized(41041041041040) + BCH_Checksum_of_Randomized) + STOP
    original_data_r = bytes.fromhex("41041041041040")
    randomized_for_bch = bytearray(original_data_r)
    RandomizerAlgorithm.randomize_cltu(randomized_for_bch, 0, 7) # DE83A1EA7F21B3
    bch_encoded_r = BchCltuAlgorithm.encode_cltu_block(bytes(randomized_for_bch))
    cltu_stream_randomized = CltuDecoder.START_SEQUENCE + bch_encoded_r + CltuDecoder.STOP_SEQUENCE

    decoder_randomized = CltuDecoder(randomize=True)
    decoded_data_r = decoder_randomized.apply(cltu_stream_randomized)
    print(f"Decoded (randomized): {decoded_data_r.hex().upper()}")
    assert decoded_data_r == original_data_r
    print("Randomized decode test PASSED.")

    # Test with padding and multiple blocks (non-randomized)
    original_10b_data_nr = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A'
    block1_nr = original_10b_data_nr[0:7]
    block2_unpadded_nr = original_10b_data_nr[7:10]
    block2_padded_nr = block2_unpadded_nr + bytes([CltuDecoder.FILLER_BYTE] * (7-len(block2_unpadded_nr)))
    
    bch1_nr = BchCltuAlgorithm.encode_cltu_block(block1_nr)
    bch2_nr = BchCltuAlgorithm.encode_cltu_block(block2_padded_nr)
    cltu_10b_stream_nr = CltuDecoder.START_SEQUENCE + bch1_nr + bch2_nr + CltuDecoder.STOP_SEQUENCE
    
    decoded_10b_data_nr = decoder_non_randomized.apply(cltu_10b_stream_nr)
    print(f"Decoded 10-byte data (non-randomized): {decoded_10b_data_nr.hex().upper()}")
    assert decoded_10b_data_nr == original_10b_data_nr
    print("Multi-block non-randomized decode test PASSED.")

    # Test error: No start sequence
    try:
        decoder_non_randomized.apply(bch_encoded_nr + CltuDecoder.STOP_SEQUENCE)
        assert False, "Should have raised error for missing start sequence"
    except ValueError as e:
        print(f"Caught expected error: {e}")
        assert "Start Sequence" in str(e)
    print("Missing start sequence test PASSED.")

    # Test error: No stop sequence
    try:
        decoder_non_randomized.apply(CltuDecoder.START_SEQUENCE + bch_encoded_nr)
        assert False, "Should have raised error for missing stop sequence"
    except ValueError as e:
        print(f"Caught expected error: {e}")
        assert "Stop Sequence" in str(e)
    print("Missing stop sequence test PASSED.")
    
    # Test error: Corrupted BCH block
    corrupted_bch_block = bytearray(bch_encoded_nr)
    corrupted_bch_block[7] ^= 0xFF # Corrupt checksum
    cltu_corrupted_stream = CltuDecoder.START_SEQUENCE + bytes(corrupted_bch_block) + CltuDecoder.STOP_SEQUENCE
    try:
        decoder_non_randomized.apply(cltu_corrupted_stream)
        assert False, "Should have raised error for BCH mismatch"
    except ValueError as e:
        print(f"Caught expected error: {e}")
        assert "checksum mismatch" in str(e) # From BchCltuAlgorithm
    print("Corrupted BCH block test PASSED.")
    
    print("CltuDecoder tests completed.")
