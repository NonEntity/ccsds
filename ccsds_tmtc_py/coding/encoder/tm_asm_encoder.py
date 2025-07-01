from ccsds_tmtc_py.coding.i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame
from typing import TypeVar

T = TypeVar('T', bound=AbstractTransferFrame)

class TmAsmEncoder(IEncodingFunction[T]):
  DEFAULT_ATTACHED_SYNC_MARKER = b'\x1A\xCF\xFC\x1D'
  
  def __init__(self, asm: bytes = DEFAULT_ATTACHED_SYNC_MARKER):
    self._asm = asm
    
  def apply(self, original_frame: T, current_data: bytes) -> bytes:
    return self._asm + current_data
