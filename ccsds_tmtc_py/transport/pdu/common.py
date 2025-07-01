from enum import Enum

class SequenceFlagType(Enum):
    """
    Indicates the segmentation status of a packet.
    These are generic terms for segment parts.
    """
    CONTINUE_SEGMENT = 0  # The packet is a continuation segment of a user data unit
    FIRST_SEGMENT = 1     # The packet is the first segment of a user data unit
    LAST_SEGMENT = 2      # The packet is the last segment of a user data unit
    UNSEGMENTED = 3       # The packet contains a complete, unsegmented user data unit
