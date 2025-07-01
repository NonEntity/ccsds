from ccsds_tmtc_py.coding.i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame # For T type hint
from ccsds_tmtc_py.algorithm.randomizer_algorithm import RandomizerAlgorithm
from typing import TypeVar

T = TypeVar('T', bound=AbstractTransferFrame)

class TmRandomizerEncoder(IEncodingFunction[T]):
  def apply(self, original_frame: T, current_data: bytes) -> bytes:
    if not current_data: return b''
    data_copy = bytearray(current_data)
    RandomizerAlgorithm.randomize_frame_tm(data_copy) # Modifies in-place
    return bytes(data_copy)
