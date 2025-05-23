from typing import Generic, TypeVar, List, Callable
from .i_decoding_function import IDecodingFunction
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame, IllegalStateException

T_ChannelDecoder = TypeVar('T_ChannelDecoder', bound=AbstractTransferFrame) # Renamed

class ChannelDecoder(Generic[T_ChannelDecoder]):
  def __init__(self, frame_decoder: IDecodingFunction[T_ChannelDecoder]):
    if frame_decoder is None:
      raise ValueError("Frame decoder must be set") # Changed from NullPointerException
    self._frame_decoder: IDecodingFunction[T_ChannelDecoder] = frame_decoder
    self._sequential_decoders: List[Callable[[bytes], bytes]] = []
    self._configured: bool = False

  @staticmethod
  def create(frame_decoder: IDecodingFunction[T_ChannelDecoder]) -> 'ChannelDecoder[T_ChannelDecoder]':
    return ChannelDecoder(frame_decoder)

  def add_decoding_function(self, func: Callable[[bytes], bytes]) -> 'ChannelDecoder[T_ChannelDecoder]':
    if self._configured:
      raise IllegalStateException("Channel decoder already configured")
    self._sequential_decoders.append(func)
    return self
  
  def configure(self) -> 'ChannelDecoder[T_ChannelDecoder]':
    self._configured = True
    return self

  def apply(self, item: bytes) -> T_ChannelDecoder:
    if not self._configured:
      raise IllegalStateException("Channel decoder not configured yet")
    
    if item is None:
        raise ValueError("Input item cannot be None.")

    to_decode = item
    
    for func in self._sequential_decoders:
      to_decode = func(to_decode)
    return self._frame_decoder.apply(to_decode)
