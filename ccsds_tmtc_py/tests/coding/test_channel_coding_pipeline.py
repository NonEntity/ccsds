import unittest
import struct
from ccsds_tmtc_py.coding.channel_encoder import ChannelEncoder
from ccsds_tmtc_py.coding.channel_decoder import ChannelDecoder
from ccsds_tmtc_py.coding.i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.coding.i_decoding_function import IDecodingFunction
from ccsds_tmtc_py.coding.encoder.tm_asm_encoder import TmAsmEncoder
from ccsds_tmtc_py.coding.decoder.tm_asm_decoder import TmAsmDecoder
from ccsds_tmtc_py.coding.encoder.tm_randomizer_encoder import TmRandomizerEncoder
from ccsds_tmtc_py.coding.decoder.tm_randomizer_decoder import TmRandomizerDecoder
from ccsds_tmtc_py.coding.encoder.cltu_encoder import CltuEncoder
from ccsds_tmtc_py.coding.decoder.cltu_decoder import CltuDecoder
from ccsds_tmtc_py.coding.encoder.reed_solomon_encoder import ReedSolomonEncoder
from ccsds_tmtc_py.coding.decoder.reed_solomon_decoder import ReedSolomonDecoder
from ccsds_tmtc_py.datalink.pdu.tm_transfer_frame import TmTransferFrame
# from ccsds_tmtc_py.datalink.pdu.tc_transfer_frame import TcTransferFrame # For type hints if needed
from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm
from ccsds_tmtc_py.algorithm.reed_solomon_algorithm import ReedSolomonAlgorithm
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException, AbstractTransferFrame # Added AbstractTransferFrame

class TestChannelCodingPipeline(unittest.TestCase):
  def test_tm_randomizer_encoder_decoder_direct(self):
    data = b"testdata12345678" # Longer to see effect
    encoder = TmRandomizerEncoder()
    decoder = TmRandomizerDecoder()
    # Create a dummy frame for the encoder's type hint satisfaction
    class DummyFrame(AbstractTransferFrame):
        def __init__(self, data_bytes): self._data = data_bytes
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

    dummy_original_frame = DummyFrame(data)
    randomized = encoder.apply(dummy_original_frame, data)
    self.assertNotEqual(data, randomized, "Randomized data should be different (with placeholder impl)")
    self.assertEqual(len(data), len(randomized))
    derandomized = decoder.apply(randomized)
    self.assertEqual(data, derandomized, "Derandomized data should match original (with placeholder impl)")

  def test_tm_asm_encoder_decoder_direct(self):
    data = b"framedata"
    asm = TmAsmEncoder.DEFAULT_ATTACHED_SYNC_MARKER
    encoder = TmAsmEncoder()
    decoder = TmAsmDecoder(strip_asm=True)
    # Dummy frame for encoder
    dummy_original_frame = TestChannelCodingPipeline.DummyTestFrame(data) # Use helper class
    with_asm = encoder.apply(dummy_original_frame, data)
    self.assertEqual(asm + data, with_asm)
    without_asm = decoder.apply(with_asm)
    self.assertEqual(data, without_asm)
    with self.assertRaises(ValueError): decoder.apply(b"wrongasm" + data)

  def test_cltu_encoder_decoder_direct_no_randomization(self):
    tc_frame_data = b"TCFRAME" * 3 # 21 bytes
    encoder = CltuEncoder(randomize=False)
    decoder = CltuDecoder(randomize=False)
    dummy_original_frame = TestChannelCodingPipeline.DummyTestFrame(tc_frame_data)
    cltu_bytes = encoder.apply(dummy_original_frame, tc_frame_data)
    self.assertTrue(cltu_bytes.startswith(CltuEncoder.START_SEQUENCE))
    self.assertTrue(cltu_bytes.endswith(CltuEncoder.STOP_SEQUENCE))
    decoded_frame_data = decoder.apply(cltu_bytes)
    self.assertEqual(tc_frame_data, decoded_frame_data)
    
    tc_frame_data_short = b"short"
    dummy_short_frame = TestChannelCodingPipeline.DummyTestFrame(tc_frame_data_short)
    cltu_bytes_short = encoder.apply(dummy_short_frame, tc_frame_data_short)
    decoded_short = decoder.apply(cltu_bytes_short)
    self.assertEqual(tc_frame_data_short, decoded_short)

  def test_cltu_encoder_decoder_direct_with_randomization(self):
    tc_frame_data = b"RANDOMTC7" * 5 # 35 bytes
    encoder = CltuEncoder(randomize=True)
    decoder = CltuDecoder(randomize=True)
    dummy_original_frame = TestChannelCodingPipeline.DummyTestFrame(tc_frame_data)
    cltu_bytes = encoder.apply(dummy_original_frame, tc_frame_data)
    self.assertTrue(cltu_bytes.startswith(CltuEncoder.START_SEQUENCE))
    self.assertTrue(cltu_bytes.endswith(CltuEncoder.STOP_SEQUENCE))
    decoded_frame_data = decoder.apply(cltu_bytes)
    self.assertEqual(tc_frame_data, decoded_frame_data)

  def test_reed_solomon_encoder_decoder_direct(self):
    rs_algo = ReedSolomonAlgorithm.create_tm_reed_solomon_255_223()
    data = bytes([i % 250 for i in range(rs_algo.K)])
    encoder = ReedSolomonEncoder(rs_algo)
    decoder = ReedSolomonDecoder(rs_algo)
    dummy_original_frame = TestChannelCodingPipeline.DummyTestFrame(data)
    codeword = encoder.apply(dummy_original_frame, data)
    self.assertEqual(len(codeword), rs_algo.N)
    self.assertNotEqual(codeword[rs_algo.K:], bytes(rs_algo.N - rs_algo.K), 
                        "Check symbols should not be all zeros with current placeholder")
    decoded_data = decoder.apply(codeword)
    self.assertEqual(data, decoded_data)
    
    corrupted_codeword = bytearray(codeword)
    if rs_algo.N > rs_algo.K : corrupted_codeword[rs_algo.N -1] ^= 0xFF
    with self.assertRaises(ValueError): decoder.apply(bytes(corrupted_codeword))

  class DummyTestFrame(AbstractTransferFrame): # Helper for type hints
      def __init__(self, data_bytes, fecf=False, ocf=False): 
          super().__init__(data_bytes, fecf)
          self.ocf_present = ocf
          self.data_field_start = 0
          self.data_field_length = len(data_bytes)
      def get_frame(self): return self._frame
      def get_frame_copy(self): return self._frame[:]
      def is_idle_frame(self): return False


  def test_channel_encoder_pipeline(self):
    # Use a valid minimal TM frame for dummy_tm_frame
    original_payload = b"pipelinedata"
    hdr_part1 = (0 << 14) | (0xAB << 4) | (0 << 1) | 0 # No OCF
    mcfc = 0; vcfc = 0;
    hdr_part2 = (0 << 15) | (0 << 14) | (0 << 13) | (3 << 11) | TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET
    dummy_tm_bytes = struct.pack(">HBBH", hdr_part1, mcfc, vcfc, hdr_part2) + original_payload
    dummy_tm_frame = TmTransferFrame(dummy_tm_bytes, fecf_present=False)
        
    encoder = ChannelEncoder[TmTransferFrame](frame_copy=True)
    encoder.add_encoding_function(TmRandomizerEncoder())
    encoder.add_encoding_function(TmAsmEncoder(asm=b"ASM_"))
    encoder.configure()
        
    original_frame_bytes = dummy_tm_frame.get_frame()
    encoded_data = encoder.apply(dummy_tm_frame)
        
    self.assertTrue(encoded_data.startswith(b"ASM_"))
    randomized_part_in_encoded = encoded_data[4:]
    self.assertNotEqual(randomized_part_in_encoded, original_frame_bytes, "Randomized part should differ from original frame")
    
    manually_randomized_original = bytearray(original_frame_bytes)
    RandomizerAlgorithm.randomize_frame_tm(manually_randomized_original) # Uses placeholder
    self.assertEqual(randomized_part_in_encoded, bytes(manually_randomized_original), 
                     "Encoded data's randomized part does not match manual randomization (placeholder check)")

  class CapturingFinalDecoder(IDecodingFunction[TmTransferFrame]):
      def __init__(self):
          self.received_data = None
      def apply(self, processed_data: bytes) -> TmTransferFrame:
          self.received_data = processed_data
          # Construct a valid minimal TmTransferFrame for return type
          hdr_part1 = 0; mcfc = 0; vcfc = 0;
          hdr_part2 = (3 << 11) | TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET # NoSeg, NoPkt
          # Ensure processed_data can be validly appended for a TmTransferFrame
          # This part might need adjustment if TmTransferFrame is very strict on length vs. FHP
          # For testing the pipeline, the key is that `processed_data` is correct.
          # If processed_data is short, this might fail.
          # Let's ensure dummy_bytes is at least header length.
          min_len_payload = processed_data
          if len(processed_data) == 0 and processed_data != b'': # handle cases for no packet
              # If FHP is NO_PACKET, data length field can be 0 -> total length 6
              # PDU length field (in header) is (len(user_data) -1), so 0xFFFF for 0 user_data
              hdr_part2 = (3 << 11) | TmTransferFrame.TM_FIRST_HEADER_POINTER_NO_PACKET
              min_len_payload = b'' # No user data
          
          # Make sure the frame is long enough for the header
          dummy_header = struct.pack(">HBBH", hdr_part1, mcfc, vcfc, hdr_part2)
          dummy_bytes = dummy_header + min_len_payload
          return TmTransferFrame(dummy_bytes, fecf_present=False)


  def test_channel_decoder_pipeline(self):
    original_payload = b"finalpipelinedata"
    
    # Data that will be fed into ChannelDecoder.apply()
    # 1. Original payload
    # 2. After TmRandomizerDecoder (so, it was randomized before)
    data_to_feed_randomizer_decoder = bytearray(original_payload)
    RandomizerAlgorithm.randomize_frame_tm(data_to_feed_randomizer_decoder) # Randomized
    # 3. After TmAsmDecoder (so, it had ASM before)
    data_to_feed_asm_decoder = b"ASM_" + bytes(data_to_feed_randomizer_decoder)
    
    final_decoder_instance = TestChannelCodingPipeline.CapturingFinalDecoder()
    decoder = ChannelDecoder[TmTransferFrame](final_decoder_instance)
    decoder.add_decoding_function(TmAsmDecoder(asm=b"ASM_", strip_asm=True))
    decoder.add_decoding_function(TmRandomizerDecoder())
    decoder.configure()
        
    decoder.apply(data_to_feed_asm_decoder) # This will call final_decoder_instance.apply eventually
    self.assertEqual(original_payload, final_decoder_instance.received_data)

  def test_channel_encoder_decoder_config_errors(self):
    encoder = ChannelEncoder().configure()
    dummy_encoder_func = TmRandomizerEncoder() # Needs a concrete IEncodingFunction
    with self.assertRaises(IllegalStateException): encoder.add_encoding_function(dummy_encoder_func)
    
    # For ChannelDecoder, the final decoder needs to be an IDecodingFunction instance
    class DummyFinal(IDecodingFunction[TmTransferFrame]):
        def apply(self, data: bytes) -> TmTransferFrame: return TestChannelCodingPipeline.DummyTestFrame(data) # type: ignore
            
    decoder = ChannelDecoder(DummyFinal()).configure() 
    with self.assertRaises(IllegalStateException): decoder.add_decoding_function(lambda x: x)
    
    # Test apply not configured
    dummy_frame_for_apply = TestChannelCodingPipeline.DummyTestFrame(b"data")
    with self.assertRaises(IllegalStateException): ChannelEncoder().apply(dummy_frame_for_apply)
    with self.assertRaises(IllegalStateException): ChannelDecoder(DummyFinal()).apply(b"")
    
    # Test constructor error for ChannelDecoder
    with self.assertRaises(ValueError): ChannelDecoder(None) # type: ignore

if __name__ == '__main__':
    unittest.main()
