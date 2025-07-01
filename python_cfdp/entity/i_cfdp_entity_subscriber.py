from abc import ABC, abstractmethod

from .indication import ICfdpIndication


class ICfdpEntitySubscriber(ABC):
    """Subscriber of CFDP entity indications."""

    @abstractmethod
    def indication(self, emitter: 'ICfdpEntity', indication: ICfdpIndication) -> None:
        pass
