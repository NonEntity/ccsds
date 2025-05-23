from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm

class TmRandomizerDecoder:
  def apply(self, data: bytes) -> bytes:
    if not data: return b''
    data_copy = bytearray(data)
    RandomizerAlgorithm.randomize_frame_tm(data_copy) # Modifies in-place
    return bytes(data_copy)
  
  def __call__(self, data: bytes) -> bytes:
    return self.apply(data)
