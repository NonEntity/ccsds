from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..condition_code import ConditionCode
from ..tlvs import MessageToUserTLV, FilestoreRequestTLV
from ..fault_handler_action import FaultHandlerAction
from .i_cfdp_request import ICfdpRequest


@dataclass
class PutRequest(ICfdpRequest):
    """Request to transfer a file to a remote CFDP entity."""

    destination_cfdp_entity_id: int
    source_file_name: Optional[str]
    destination_file_name: Optional[str]
    segmentation_control: bool = False
    flow_label: Optional[bytes] = None
    acknowledged_transmission_mode: Optional[bool] = None
    closure_requested: Optional[bool] = None
    message_to_user_list: List[MessageToUserTLV] = field(default_factory=list)
    fault_handler_override_map: Dict[ConditionCode, FaultHandlerAction] = field(default_factory=dict)
    filestore_request_list: List[FilestoreRequestTLV] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        destination_cfdp_entity_id: int,
        source_file_name: Optional[str],
        destination_file_name: Optional[str],
        segmentation_control: bool,
        flow_label: Optional[bytes],
    ) -> "PutRequest":
        """Create a basic request with default options."""

        return cls(
            destination_cfdp_entity_id=destination_cfdp_entity_id,
            source_file_name=source_file_name,
            destination_file_name=destination_file_name,
            segmentation_control=segmentation_control,
            flow_label=flow_label,
        )

    def __str__(self) -> str:  # pragma: no cover - simple representation
        flow = list(self.flow_label) if self.flow_label is not None else None
        return (
            "PutRequest{"
            f"destination_cfdp_entity_id={self.destination_cfdp_entity_id}, "
            f"source_file_name='{self.source_file_name}', "
            f"destination_file_name='{self.destination_file_name}', "
            f"segmentation_control={self.segmentation_control}, "
            f"fault_handler_override_map={self.fault_handler_override_map}, "
            f"flow_label={flow}, "
            f"acknowledged_transmission_mode={self.acknowledged_transmission_mode}, "
            f"closure_requested={self.closure_requested}, "
            f"message_to_user_list={self.message_to_user_list}, "
            f"filestore_request_list={self.filestore_request_list}"
            "}"
        )
