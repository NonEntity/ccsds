import struct
from ccsds_tmtc_py.ocf.pdu.clcw import Clcw, CopEffectType

class ClcwBuilder:
    """
    Builder class for creating CLCW (Communications Link Control Word) instances.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        """Resets all CLCW fields to their default values."""
        self._status_field: int = 0  # 3 bits
        self._cop_in_effect: CopEffectType = CopEffectType.NONE # 2 bits, use enum
        self._virtual_channel_id: int = 0  # 6 bits
        self._reserved_spare: int = 0  # 2 bits (Octet 1, bits 0-1)
        self._no_rf_available_flag: bool = False
        self._no_bitlock_flag: bool = False
        self._lockout_flag: bool = False
        self._wait_flag: bool = False
        self._retransmit_flag: bool = False
        self._farm_b_counter: int = 0  # 2 bits
        # Bit 0 of Octet 2 is spare, assumed 0
        self._report_value: int = 0  # 8 bits
        return self

    @staticmethod
    def create() -> 'ClcwBuilder':
        """Static factory method to create a ClcwBuilder."""
        return ClcwBuilder()

    def set_status_field(self, status_field: int) -> 'ClcwBuilder':
        if not (0 <= status_field <= 0x07): # 3 bits
            raise ValueError("Status Field must be a 3-bit value (0-7).")
        self._status_field = status_field
        return self

    def set_cop_in_effect(self, cop_effect: CopEffectType) -> 'ClcwBuilder':
        """Sets the COP In Effect field using the CopEffectType enum."""
        self._cop_in_effect = cop_effect
        return self
    
    def set_cop1_in_effect(self, cop1_active: bool) -> 'ClcwBuilder':
        """
        Helper to set COP In Effect based on a boolean for COP-1.
        If true, sets COP-1. If false, sets NONE.
        """
        self._cop_in_effect = CopEffectType.COP1 if cop1_active else CopEffectType.NONE
        return self

    def set_virtual_channel_id(self, virtual_channel_id: int) -> 'ClcwBuilder':
        if not (0 <= virtual_channel_id <= 0x3F): # 6 bits
            raise ValueError("Virtual Channel ID must be a 6-bit value (0-63).")
        self._virtual_channel_id = virtual_channel_id
        return self

    def set_reserved_spare(self, reserved_spare: int) -> 'ClcwBuilder':
        if not (0 <= reserved_spare <= 0x03): # 2 bits
            raise ValueError("Reserved Spare (Octet 1, bits 0-1) must be a 2-bit value (0-3).")
        self._reserved_spare = reserved_spare
        return self

    def set_no_rf_available_flag(self, flag: bool) -> 'ClcwBuilder':
        self._no_rf_available_flag = flag
        return self

    def set_no_bitlock_flag(self, flag: bool) -> 'ClcwBuilder':
        self._no_bitlock_flag = flag
        return self

    def set_lockout_flag(self, flag: bool) -> 'ClcwBuilder':
        self._lockout_flag = flag
        return self

    def set_wait_flag(self, flag: bool) -> 'ClcwBuilder':
        self._wait_flag = flag
        return self

    def set_retransmit_flag(self, flag: bool) -> 'ClcwBuilder':
        self._retransmit_flag = flag
        return self

    def set_farm_b_counter(self, farm_b_counter: int) -> 'ClcwBuilder':
        if not (0 <= farm_b_counter <= 0x03): # 2 bits
            raise ValueError("FARM-B Counter must be a 2-bit value (0-3).")
        self._farm_b_counter = farm_b_counter
        return self

    def set_report_value(self, report_value: int) -> 'ClcwBuilder':
        if not (0 <= report_value <= 0xFF): # 8 bits
            raise ValueError("Report Value must be an 8-bit value (0-255).")
        self._report_value = report_value
        return self

    def build(self) -> Clcw:
        """
        Builds the CLCW object from the configured fields.
        CLCW format (CCSDS 232.0-B-3, section 4.2):
        - Octet 0: Control Word Type (0 for CLCW), Version (00), Status Field (3 bits), COP In Effect (2 bits)
        - Octet 1: Virtual Channel ID (6 bits), Reserved Spare (2 bits)
        - Octet 2: No RF Avail (1b), No Bit Lock (1b), Lockout (1b), Wait (1b), Retransmit (1b), FARM-B (2b), Spare (1b)
        - Octet 3: Report Value (8 bits)
        """
        # Octet 0: Control Word Type (bit 7) is 0 for CLCW. Version (bits 6-5) is 00.
        byte0 = 0x00  # CLCW Type = 0, Version = 00
        byte0 |= (self._status_field & 0x07) << 2  # Status Field (bits 4-2)
        byte0 |= (self._cop_in_effect.value & 0x03) # COP In Effect (bits 1-0)

        # Octet 1
        byte1 = 0x00
        byte1 |= (self._virtual_channel_id & 0x3F) << 2  # Virtual Channel ID (bits 7-2)
        byte1 |= (self._reserved_spare & 0x03)          # Reserved Spare (bits 1-0)

        # Octet 2
        byte2 = 0x00
        if self._no_rf_available_flag: byte2 |= 0x80 # Bit 7
        if self._no_bitlock_flag:      byte2 |= 0x40 # Bit 6
        if self._lockout_flag:         byte2 |= 0x20 # Bit 5
        if self._wait_flag:            byte2 |= 0x10 # Bit 4
        if self._retransmit_flag:      byte2 |= 0x08 # Bit 3
        byte2 |= (self._farm_b_counter & 0x03) << 1   # FARM-B Counter (bits 2-1)
        # Bit 0 is spare, remains 0.

        # Octet 3
        byte3 = self._report_value & 0xFF

        clcw_bytes = bytes([byte0, byte1, byte2, byte3])
        return Clcw(clcw_bytes)

if __name__ == '__main__':
    # Example Usage
    builder = ClcwBuilder.create()
    builder.set_status_field(1)
    builder.set_cop_in_effect(CopEffectType.COP1) # Or builder.set_cop1_in_effect(True)
    builder.set_virtual_channel_id(5)
    builder.set_reserved_spare(0)
    builder.set_no_rf_available_flag(False)
    builder.set_no_bitlock_flag(False)
    builder.set_lockout_flag(False)
    builder.set_wait_flag(True)
    builder.set_retransmit_flag(False)
    builder.set_farm_b_counter(2)
    builder.set_report_value(0xAA)

    clcw = builder.build()
    print(f"Built CLCW: {clcw}")
    print(f"  Raw bytes: {clcw.ocf.hex().upper()}") # Expected: 051414AA

    assert clcw.status_field == 1
    assert clcw.cop_in_effect == CopEffectType.COP1
    assert clcw.virtual_channel_id == 5
    assert clcw.wait_flag is True
    assert clcw.farm_b_counter == 2
    assert clcw.report_value == 0xAA
    
    # Test reset
    builder.reset()
    clcw_reset = builder.build()
    print(f"Reset CLCW: {clcw_reset}")
    print(f"  Raw bytes (reset): {clcw_reset.ocf.hex().upper()}") # Expected: 00000000
    assert clcw_reset.status_field == 0
    assert clcw_reset.cop_in_effect == CopEffectType.NONE

    print("ClcwBuilder tests completed.")
