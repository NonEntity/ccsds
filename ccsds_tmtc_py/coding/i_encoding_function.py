import abc
from typing import Generic, TypeVar
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import AbstractTransferFrame

T = TypeVar('T', bound=AbstractTransferFrame)

class IEncodingFunction(Generic[T], abc.ABC):
  @abc.abstractmethod
  def apply(self, original_frame: T, current_data: bytes) -> bytes:
    pass
