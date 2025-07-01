from ccsds_tmtc_py.algorithm.reed_solomon_algorithm import ReedSolomonAlgorithm

class ReedSolomonDecoder:
  def __init__(self, rs_algorithm: ReedSolomonAlgorithm):
    self._rs_algorithm = rs_algorithm
    
  def apply(self, data: bytes) -> bytes:
    # Assumes data is the full codeword (N bytes for the configured RS alg)
    return self._rs_algorithm.decode(data)
  
  def __call__(self, data: bytes) -> bytes:
    return self.apply(data)
