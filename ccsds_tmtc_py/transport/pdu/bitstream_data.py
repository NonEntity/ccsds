class BitstreamData:
    """
    Represents a container for bitstream data, where the length is specified in bits.
    This is often used in conjunction with AOS Transfer Frames using B_PDU User Data Type.
    """
    def __init__(self, data: bytes, num_bits: int):
        """
        Initializes the BitstreamData object.

        Args:
            data: The byte string containing the bitstream. The length of this byte string
                  must be sufficient to hold num_bits.
            num_bits: The actual number of bits in the bitstream.

        Raises:
            ValueError: If the length of 'data' is less than the minimum required bytes
                        to store 'num_bits'.
        """
        if data is None:
            raise ValueError("Data cannot be None.")
        if num_bits < 0:
            raise ValueError("Number of bits cannot be negative.")

        required_bytes = (num_bits + 7) // 8
        if len(data) < required_bytes:
            raise ValueError(
                f"Length of data ({len(data)} bytes) is insufficient for the specified "
                f"number of bits ({num_bits}, requires {required_bytes} bytes)."
            )

        self._data: bytes = data
        self._num_bits: int = num_bits
        self._is_invalid_flag: bool = False

    @staticmethod
    def invalid() -> 'BitstreamData':
        """
        Factory method to create an 'invalid' BitstreamData object.
        An invalid BitstreamData might represent a scenario where bitstream
        extraction failed or is not applicable.
        """
        obj = BitstreamData(b'', 0)
        obj._is_invalid_flag = True
        return obj

    @property
    def data(self) -> bytes:
        """Returns the raw byte string containing the bitstream."""
        return self._data

    @property
    def num_bits(self) -> int:
        """Returns the number of valid bits in the bitstream."""
        return self._num_bits

    @property
    def is_invalid(self) -> bool:
        """
        Returns True if this BitstreamData object is marked as invalid,
        False otherwise.
        """
        return self._is_invalid_flag

    def __repr__(self) -> str:
        if self.is_invalid:
            return "BitstreamData(invalid)"
        return f"BitstreamData(num_bits={self.num_bits}, data_len_bytes={len(self.data)})"

    def __str__(self) -> str:
        return self.__repr__()

# Example Usage
if __name__ == '__main__':
    # Valid bitstream
    try:
        bs_data_bytes = b"\xAA\xBB\xCC" # 3 bytes = 24 bits
        bs = BitstreamData(bs_data_bytes, 20) # Using only 20 bits from the 24 available
        print(f"Valid Bitstream: {bs}")
        print(f"  Data (hex): {bs.data.hex()}")
        print(f"  Num Bits: {bs.num_bits}")
        print(f"  Is Invalid: {bs.is_invalid}")
        assert len(bs.data) == 3
        assert bs.num_bits == 20
    except ValueError as e:
        print(f"Error (valid): {e}")

    # Bitstream using full byte length
    try:
        bs_full = BitstreamData(bs_data_bytes, 24)
        print(f"Valid Bitstream (full): {bs_full}")
        assert bs_full.num_bits == 24
    except ValueError as e:
        print(f"Error (full): {e}")

    # Invalid bitstream
    invalid_bs = BitstreamData.invalid()
    print(f"Invalid Bitstream: {invalid_bs}")
    print(f"  Data: {invalid_bs.data}")
    print(f"  Num Bits: {invalid_bs.num_bits}")
    print(f"  Is Invalid: {invalid_bs.is_invalid}")
    assert invalid_bs.is_invalid
    assert invalid_bs.num_bits == 0
    assert len(invalid_bs.data) == 0

    # Error case: data too short for num_bits
    try:
        BitstreamData(b"\xAA", 10) # 1 byte data, 10 bits specified (needs 2 bytes)
    except ValueError as e:
        print(f"Error (data too short): {e}")
    
    # Error case: num_bits negative
    try:
        BitstreamData(b"\xAA", -1)
    except ValueError as e:
        print(f"Error (negative num_bits): {e}")

    # Error case: data is None
    try:
        BitstreamData(None, 10) # type: ignore
    except ValueError as e:
        print(f"Error (data is None): {e}")
