from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..condition_code import ConditionCode
from ..fault_declared_exception import FaultDeclaredException
from ..util.simple_transaction_id_generator import SimpleTransactionIdGenerator
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
    message_to_user_list: List[bytes] = field(default_factory=list)
    fault_handler_override_map: Dict[ConditionCode, str] = field(default_factory=dict)
    filestore_request_list: List[bytes] = field(default_factory=list)
