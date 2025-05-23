from enum import Enum
from .abstract_ocf import AbstractOcf

class CopEffectType(Enum):
    """
    Indicates the type of COP (Communications Operation Procedure) in effect.
    """
    NONE = 0        # COP-NONE or No SLP in effect
    COP1 = 1        # COP-1 (FARM-1 and/or FOP-1) in effect
    RESERVED2 = 2   # Reserved
    RESERVED3 = 3   # Reserved

class Clcw(AbstractOcf):
    """
    Communications Link Control Word (CLCW).
    The CLCW is a 4-octet field reported on the return link, providing status
    information about the forward link and its associated virtual channel.
    """
    CLCW_LENGTH = 4

    def __init__(self, ocf_data: bytes):
        """
        Initializes the CLCW object from the provided OCF data.

        Args:
            ocf_data: The 4-octet OCF data representing the CLCW.

        Raises:
            ValueError: If ocf_data is None, not 4 bytes long, not a CLCW (based on type bit),
                        or if the CLCW version number is not 0.
        """
        super().__init__(ocf_data)

        if not self.is_clcw:
            raise ValueError("OCF data is not a CLCW (Control Word Type bit is not 0).")
        if len(self.ocf) != self.CLCW_LENGTH: # self.ocf is from superclass AbstractOcf
            raise ValueError(f"CLCW data must be {self.CLCW_LENGTH} bytes long, got {len(self.ocf)}.")

        # Octet 0
        self._version_number: int = (self.ocf[0] & 0x60) >> 5
        if self._version_number != 0:
            raise ValueError(f"Invalid CLCW version number: {self._version_number}, expected 0.")
        
        self._status_field: int = (self.ocf[0] & 0x1C) >> 2
        self._cop_in_effect: CopEffectType = CopEffectType((self.ocf[0] & 0x03))

        # Octet 1
        self._virtual_channel_id: int = (self.ocf[1] & 0xFC) >> 2
        self._reserved_spare: int = self.ocf[1] & 0x03 # Spare bits

        # Octet 2
        self._no_rf_available_flag: bool = (self.ocf[2] & 0x80) != 0
        self._no_bitlock_flag: bool = (self.ocf[2] & 0x40) != 0
        self._lockout_flag: bool = (self.ocf[2] & 0x20) != 0
        self._wait_flag: bool = (self.ocf[2] & 0x10) != 0
        self._retransmit_flag: bool = (self.ocf[2] & 0x08) != 0
        self._farm_b_counter: int = (self.ocf[2] & 0x06) >> 1
        # Bit 0 of Octet 2 is spare

        # Octet 3
        self._report_value: int = self.ocf[3]

    @property
    def version_number(self) -> int:
        """CLCW Version Number (2 bits). Should be 0."""
        return self._version_number

    @property
    def status_field(self) -> int:
        """Status Field (3 bits). Meaning is COP-dependent."""
        return self._status_field

    @property
    def cop_in_effect(self) -> CopEffectType:
        """COP In Effect (2 bits). Indicates which COP is active."""
        return self._cop_in_effect

    @property
    def virtual_channel_id(self) -> int:
        """Virtual Channel Identification (6 bits)."""
        return self._virtual_channel_id

    @property
    def reserved_spare1(self) -> int: # Java: getReservedSpare()
        """Reserved/Spare bits in Octet 1 (2 bits)."""
        return self._reserved_spare
    
    # Note: Java class has getSpare() for bit 0 of Octet 2.
    # This is not explicitly requested by the task, so omitting for now.

    @property
    def no_rf_available_flag(self) -> bool:
        """'No RF Available' Flag (1 bit). True if no RF is available."""
        return self._no_rf_available_flag

    @property
    def no_bitlock_flag(self) -> bool:
        """'No Bit Lock' Flag (1 bit). True if no bit lock is achieved."""
        return self._no_bitlock_flag

    @property
    def lockout_flag(self) -> bool:
        """'Lockout' Flag (1 bit). True if the FOP state machine is in Lockout."""
        return self._lockout_flag

    @property
    def wait_flag(self) -> bool:
        """'Wait' Flag (1 bit). True if the FOP state machine is in Wait state."""
        return self._wait_flag

    @property
    def retransmit_flag(self) -> bool:
        """'Retransmit' Flag (1 bit). True if retransmission is advised."""
        return self._retransmit_flag

    @property
    def farm_b_counter(self) -> int:
        """FARM-B Counter (2 bits). Used by FARM-B procedures."""
        return self._farm_b_counter

    @property
    def report_value(self) -> int:
        """Report Value (8 bits). COP-dependent information."""
        return self._report_value

    def __repr__(self) -> str:
        return (
            f"Clcw(vc_id={self.virtual_channel_id}, cop_effect={self.cop_in_effect.name}, "
            f"status={self.status_field}, farm_b={self.farm_b_counter}, report_val=0x{self.report_value:02X}, "
            f"no_rf={self.no_rf_available_flag}, no_bitlock={self.no_bitlock_flag}, "
            f"lockout={self.lockout_flag}, wait={self.wait_flag}, retransmit={self.retransmit_flag})"
        )

# Example Usage (for testing during development)
if __name__ == '__main__':
    # Example CLCW data:
    # Version 0, Status 1, COP-1, VCID 5, Spare 0
    # NoRF 0, NoBitLock 0, Lockout 0, Wait 1, Retransmit 0, FarmB 2, Spare 0
    # Report 0xAA
    # Octet 0: 000 (ver) 001 (stat) 01 (cop) -> 00000101 = 0x05
    # Octet 1: 000101 (vcid) 00 (spare) -> 00010100 = 0x14
    # Octet 2: 0 (norf) 0 (nobit) 0 (lock) 1 (wait) 0 (retr) 10 (farmb) 0 (spare) -> 00010100 = 0x14
    # Octet 3: 10101010 = 0xAA
    clcw_data_example = bytes([0x05, 0x14, 0x14, 0xAA])

    try:
        clcw_obj = Clcw(clcw_data_example)
        print(f"Parsed CLCW: {clcw_obj}")
        print(f"  Version: {clcw_obj.version_number}")
        print(f"  Status Field: {clcw_obj.status_field}")
        print(f"  COP In Effect: {clcw_obj.cop_in_effect.name} ({clcw_obj.cop_in_effect.value})")
        print(f"  Virtual Channel ID: {clcw_obj.virtual_channel_id}")
        print(f"  Reserved/Spare (Octet 1): {clcw_obj.reserved_spare1}")
        print(f"  No RF Available: {clcw_obj.no_rf_available_flag}")
        print(f"  No Bit Lock: {clcw_obj.no_bitlock_flag}")
        print(f"  Lockout: {clcw_obj.lockout_flag}")
        print(f"  Wait: {clcw_obj.wait_flag}")
        print(f"  Retransmit: {clcw_obj.retransmit_flag}")
        print(f"  FARM-B Counter: {clcw_obj.farm_b_counter}")
        print(f"  Report Value: {hex(clcw_obj.report_value)}")
        print(f"  Is CLCW: {clcw_obj.is_clcw}")
        print(f"  Raw OCF: {clcw_obj.ocf.hex().upper()}")

        # Example of invalid data (wrong length)
        try:
            Clcw(bytes([0x05, 0x14, 0x14]))
        except ValueError as e:
            print(f"Error (invalid length): {e}")

        # Example of invalid data (not a CLCW - type bit is 1)
        try:
            Clcw(bytes([0x85, 0x14, 0x14, 0xAA]))
        except ValueError as e:
            print(f"Error (not CLCW): {e}")
            
        # Example of invalid data (wrong version)
        try:
            # Version 1 (01) -> 010... -> Octet 0 starts with 0x2_
            Clcw(bytes([0x25, 0x14, 0x14, 0xAA]))
        except ValueError as e:
            print(f"Error (wrong version): {e}")

    except ValueError as e:
        print(f"Error creating CLCW: {e}")
