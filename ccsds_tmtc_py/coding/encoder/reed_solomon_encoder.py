from ccsds_tmtc_py.coding.i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame
from ccsds_tmtc_py.algorithm.reed_solomon_algorithm import ReedSolomonAlgorithm
from typing import TypeVar

T = TypeVar('T', bound=AbstractTransferFrame)

class ReedSolomonEncoder(IEncodingFunction[T]):
  def __init__(self, rs_algorithm: ReedSolomonAlgorithm):
    self._rs_algorithm = rs_algorithm
    
  def apply(self, original_frame: T, current_data: bytes) -> bytes:
    # Assumes current_data is the block to be encoded (K bytes for the configured RS alg)
    # For TM frames, this would be the Transfer Frame Primary Header + 
    # Transfer Frame Secondary Header (if present) + Transfer Frame Data Field + OCF (if present)
    # The ChannelEncoder setup is responsible for feeding the correct part of the frame 
    # if the frame is larger than K.
    # For now, we assume current_data is exactly K bytes as per algorithm's K.
    # The Java ReedSolomonEncoder doesn't have this check, it just passes data to rs.encodeData
    # Let's follow Java: pass current_data directly. The RS algo placeholder will handle length check.
    # The placeholder ReedSolomonAlgorithm.encode *does* have the length check.
    return self._rs_algorithm.encode(current_data)
