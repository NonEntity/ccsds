from typing import Generic, TypeVar, List
from .i_encoding_function import IEncodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame, IllegalStateException

T_ChannelEncoder = TypeVar('T_ChannelEncoder', bound=AbstractTransferFrame) # Renamed to avoid clash

class ChannelEncoder(Generic[T_ChannelEncoder]):
  def __init__(self, frame_copy: bool = False):
    self._frame_copy: bool = frame_copy
    self._sequential_encoders: List[IEncodingFunction[T_ChannelEncoder]] = []
    self._configured: bool = False

  @staticmethod
  def create(frame_copy: bool = False) -> 'ChannelEncoder[T_ChannelEncoder]': # Type hint with string
    return ChannelEncoder(frame_copy)

  def add_encoding_function(self, func: IEncodingFunction[T_ChannelEncoder]) -> 'ChannelEncoder[T_ChannelEncoder]':
    if self._configured:
      raise IllegalStateException("Channel encoder already configured")
    self._sequential_encoders.append(func)
    return self
  
  def configure(self) -> 'ChannelEncoder[T_ChannelEncoder]':
    self._configured = True
    return self

  def apply(self, transfer_frame: T_ChannelEncoder) -> bytes:
    if not self._configured:
      raise IllegalStateException("Channel encoder not configured yet")
    
    # Ensure transfer_frame is not None and has get_frame_copy/get_frame methods
    if transfer_frame is None:
        raise ValueError("Input transfer_frame cannot be None.")
    if not hasattr(transfer_frame, 'get_frame_copy') or not hasattr(transfer_frame, 'get_frame'):
        raise TypeError("transfer_frame must be an instance of AbstractTransferFrame or similar.")

    to_encode = transfer_frame.get_frame_copy() if self._frame_copy else transfer_frame.get_frame()
    
    for func in self._sequential_encoders:
      to_encode = func.apply(transfer_frame, to_encode)
    return to_encode
