from ccsds_tmtc_py.coding.i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame
from ccsds_tmtc_py.algorithm.bch_cltu_algorithm import BchCltuAlgorithm
from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm
from typing import TypeVar

T = TypeVar('T', bound=AbstractTransferFrame)

class CltuEncoder(IEncodingFunction[T]):
  START_SEQUENCE = b'\xEB\x90'
  STOP_SEQUENCE = b'\xC5\xC5\xC5\xC5\xC5\xC5\xC5\xC5' # 8 bytes for tail sequence
  FILLER_BYTE = 0x55

  def __init__(self, randomize: bool = True):
    self._randomize = randomize

  def apply(self, original_frame: T, current_data: bytes) -> bytes:
    # The current_data is the TC Transfer Frame (or its data part).
    # The CLTU encoding process takes this data, segments it into 7-byte blocks,
    # randomizes (conditionally), BCH encodes, and adds start/stop sequences.
    
    output_list = [self.START_SEQUENCE]
    num_data_bytes = len(current_data)
    
    if num_data_bytes == 0: # Handle empty input data
        # Even for empty data, a CLTU usually contains at least one block of filler/idle
        # or just the start/stop sequence. However, the loop below handles num_blocks=0.
        # If we want to ensure at least one filler block for empty TC frame data:
        # num_blocks = 1
        # But let's follow the logic that if num_data_bytes is 0, num_blocks will be 0.
        # The spec implies CLTU contains one or more codeblocks.
        # If current_data is empty, perhaps it should be an error or return START+STOP.
        # For now, if current_data is empty, loop won't run, returns START+STOP.
        pass


    num_blocks = (num_data_bytes + 6) // 7 # Calculate number of 7-byte blocks needed
    
    for i in range(num_blocks):
      start_idx = i * 7
      end_idx = start_idx + 7
      block_segment = current_data[start_idx:end_idx]
      
      # Pad the segment if it's shorter than 7 bytes (last block)
      block_padded_list = list(block_segment)
      while len(block_padded_list) < 7:
          block_padded_list.append(self.FILLER_BYTE)
      block_padded = bytes(block_padded_list)
      
      block_to_bch = bytearray(block_padded) # BCH algorithm might modify or needs bytearray
      
      if self._randomize:
        # CLTU randomization is applied to each 7-byte block *before* BCH encoding.
        # The RandomizerAlgorithm.randomize_cltu expects a bytearray and modifies in place.
        # It also needs start/stop octet indices within the larger data. Here, it's always 0 to 7 for the block.
        RandomizerAlgorithm.randomize_cltu(block_to_bch, 0, 7)
        
      coded_bch_block = BchCltuAlgorithm.encode_cltu_block(bytes(block_to_bch)) # encode_cltu_block expects bytes
      output_list.append(coded_bch_block)
      
    output_list.append(self.STOP_SEQUENCE)
    return b"".join(output_list)

if __name__ == '__main__':
    class DummyFrame(AbstractTransferFrame): # For testing IEncodingFunction
        def __init__(self, data): self._data = data
        def get_frame(self): return self._data
        def get_frame_copy(self): return self._data[:]
        def get_length(self): return len(self._data)
        def is_fecf_present(self): return False
        def get_fecf(self): return 0
        def is_ocf_present(self): return False
        def get_ocf_copy(self): return b''
        def get_data_field_copy(self): return self._data
        def get_data_field_length(self): return len(self._data)
        def is_valid(self): return True
        def is_idle_frame(self): return False

    encoder_randomized = CltuEncoder(randomize=True)
    encoder_non_randomized = CltuEncoder(randomize=False)

    # Test with data from CCSDS 231.0-B-3 Appendix A.3 Example
    # D(x) = 41041041041040 (hex). This is one 7-byte block.
    tc_frame_data_example = bytes.fromhex("41041041041040")
    dummy_orig_frame = DummyFrame(tc_frame_data_example)

    # Test non-randomized
    cltu_non_randomized = encoder_non_randomized.apply(dummy_orig_frame, tc_frame_data_example)
    print(f"CLTU (non-randomized) data: {tc_frame_data_example.hex()}")
    print(f"Encoded (non-randomized): {cltu_non_randomized.hex().upper()}")
    # Expected: EB90 + (41041041041040 + F6) + C5...C5
    # (where F6 is checksum for 41041041041040)
    expected_bch_block_non_rand = BchCltuAlgorithm.encode_cltu_block(tc_frame_data_example)
    assert expected_bch_block_non_rand == bytes.fromhex("41041041041040F6")
    expected_output_non_rand = CltuEncoder.START_SEQUENCE + expected_bch_block_non_rand + CltuEncoder.STOP_SEQUENCE
    assert cltu_non_randomized == expected_output_non_rand
    print("Non-randomized test PASSED.")

    # Test randomized
    # First, manually randomize the data block to see what BCH gets
    data_for_bch_manual_rand = bytearray(tc_frame_data_example)
    RandomizerAlgorithm.randomize_cltu(data_for_bch_manual_rand, 0, 7)
    # Randomized data: 41^FF=DE, 04^87=83, 10^B1=A1, 41^AF=EA, 04^7B=7F, 10^31=21, 40^F3=B3
    # So, DE83A1EA7F21B3 should go into BCH encoder
    assert data_for_bch_manual_rand == bytes.fromhex("DE83A1EA7F21B3")
    
    cltu_randomized = encoder_randomized.apply(dummy_orig_frame, tc_frame_data_example)
    print(f"CLTU (randomized) data: {tc_frame_data_example.hex()}")
    print(f"Encoded (randomized): {cltu_randomized.hex().upper()}")
    
    expected_bch_block_rand = BchCltuAlgorithm.encode_cltu_block(data_for_bch_manual_rand)
    expected_output_rand = CltuEncoder.START_SEQUENCE + expected_bch_block_rand + CltuEncoder.STOP_SEQUENCE
    assert cltu_randomized == expected_output_rand
    print("Randomized test PASSED.")

    # Test with data that needs padding
    short_data = b'\x12\x34\x56' # 3 bytes
    dummy_short_frame = DummyFrame(short_data)
    cltu_padded_non_rand = encoder_non_randomized.apply(dummy_short_frame, short_data)
    padded_block_for_bch = short_data + bytes([CltuEncoder.FILLER_BYTE] * 4) # 12345655555555
    assert padded_block_for_bch == bytes.fromhex("12345655555555")
    expected_bch_padded = BchCltuAlgorithm.encode_cltu_block(padded_block_for_bch)
    expected_output_padded_non_rand = CltuEncoder.START_SEQUENCE + expected_bch_padded + CltuEncoder.STOP_SEQUENCE
    assert cltu_padded_non_rand == expected_output_padded_non_rand
    print(f"Padded non-randomized test: {cltu_padded_non_rand.hex().upper()}")
    print("Padding test PASSED.")

    # Test with 10 bytes of data (two blocks)
    ten_byte_data = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A'
    dummy_10b_frame = DummyFrame(ten_byte_data)
    cltu_10b_non_rand = encoder_non_randomized.apply(dummy_10b_frame, ten_byte_data)
    block1 = ten_byte_data[0:7]
    block2_unpadded = ten_byte_data[7:10]
    block2_padded = block2_unpadded + bytes([CltuEncoder.FILLER_BYTE] * (7-len(block2_unpadded)))
    
    bch_block1 = BchCltuAlgorithm.encode_cltu_block(block1)
    bch_block2 = BchCltuAlgorithm.encode_cltu_block(block2_padded)
    expected_10b_output = CltuEncoder.START_SEQUENCE + bch_block1 + bch_block2 + CltuEncoder.STOP_SEQUENCE
    assert cltu_10b_non_rand == expected_10b_output
    print(f"10-byte data (2 blocks) non-randomized test: {cltu_10b_non_rand.hex().upper()}")
    print("Multi-block test PASSED.")

    print("CltuEncoder tests completed.")
