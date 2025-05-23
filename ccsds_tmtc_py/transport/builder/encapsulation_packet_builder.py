import struct
from ccsds_tmtc_py.transport.pdu.encapsulation_packet import EncapsulationPacket, EncapsulationProtocolIdType

class EncapsulationPacketBuilder:
    """
    Builder class for creating EncapsulationPacket instances.
    """
    def __init__(self, quality_indicator: bool = True):
        """
        Initializes the EncapsulationPacketBuilder.

        Args:
            quality_indicator: The quality indicator for the packets to be built.
        """
        self._quality_indicator: bool = quality_indicator
        self._protocol_id: EncapsulationProtocolIdType = EncapsulationProtocolIdType.PROTOCOL_ID_IDLE
        
        self._protocol_id_ext_present: bool = False
        self._protocol_id_ext: int = 0 # 4 bits

        self._user_defined_field_present: bool = False
        self._user_defined_field: int = 0 # 4 bits

        self._ccsds_defined_field_present: bool = False
        self._ccsds_defined_field: bytes | None = None # 2 bytes

        # -1 means dynamic based on fields present and payload length.
        # 0 means PHL=1 (1 octet total packet length)
        # 1 means PHL=2 (2 octets header, 1 octet length field)
        # 2 means PHL=4 (4 octets header, 2 octets length field)
        # 3 means PHL=8 (8 octets header, 4 octets length field)
        self._length_of_length_code: int = -1 
        
        self._payload_unit: bytes | None = None

    @staticmethod
    def create(initialiser: EncapsulationPacket = None, copy_data_field: bool = False, quality_indicator: bool = True) -> 'EncapsulationPacketBuilder':
        """
        Static factory method to create an EncapsulationPacketBuilder.
        Can initialize the builder from an existing EncapsulationPacket.
        """
        builder = EncapsulationPacketBuilder(quality_indicator=quality_indicator)
        if initialiser:
            builder.set_encapsulation_protocol_id(initialiser.encapsulation_protocol_id)
            if initialiser.encapsulation_protocol_id_extension_present:
                builder.set_encapsulation_protocol_id_extension(initialiser.encapsulation_protocol_id_extension)
            if initialiser.user_defined_field_present:
                builder.set_user_defined_field(initialiser.user_defined_field)
            if initialiser.ccsds_defined_field_present:
                builder.set_ccsds_defined_field(initialiser.ccsds_defined_field)
            
            # Determine length_of_length_code from initialiser's primary_header_length
            if initialiser.primary_header_length == 1: builder.set_length_of_length_code(0)
            elif initialiser.primary_header_length == 2: builder.set_length_of_length_code(1)
            elif initialiser.primary_header_length == 4: builder.set_length_of_length_code(2)
            elif initialiser.primary_header_length == 8: builder.set_length_of_length_code(3)

            if copy_data_field:
                builder.set_data(initialiser.get_data_field_copy())
        return builder

    def set_quality_indicator(self, quality_indicator: bool) -> 'EncapsulationPacketBuilder':
        self._quality_indicator = quality_indicator
        return self

    def set_encapsulation_protocol_id(self, protocol_id: EncapsulationProtocolIdType) -> 'EncapsulationPacketBuilder':
        self._protocol_id = protocol_id
        return self

    def set_idle(self) -> 'EncapsulationPacketBuilder':
        """Sets the packet to be an Idle Packet (Protocol ID = IDLE, PHL=1)."""
        self.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_IDLE)
        self.set_length_of_length_code(0) # PHL=1 for idle
        self.clear_data() # Idle packets usually have no payload from builder perspective
        # Clear optional fields for typical idle packet
        self._protocol_id_ext_present = False
        self._user_defined_field_present = False
        self._ccsds_defined_field_present = False
        return self

    def set_encapsulation_protocol_id_extension(self, extension: int) -> 'EncapsulationPacketBuilder':
        if not (0 <= extension <= 0x0F): # 4 bits
            raise ValueError("Encapsulation Protocol ID Extension must be a 4-bit value.")
        self._protocol_id_ext = extension
        self._protocol_id_ext_present = True
        return self

    def set_user_defined_field(self, user_field: int) -> 'EncapsulationPacketBuilder':
        if not (0 <= user_field <= 0x0F): # 4 bits
            raise ValueError("User-Defined Field must be a 4-bit value.")
        self._user_defined_field = user_field
        self._user_defined_field_present = True
        return self

    def set_ccsds_defined_field(self, ccsds_field: bytes) -> 'EncapsulationPacketBuilder':
        if len(ccsds_field) != 2:
            raise ValueError("CCSDS-Defined Field must be 2 bytes long.")
        self._ccsds_defined_field = ccsds_field
        self._ccsds_defined_field_present = True
        return self
    
    def set_length_of_length_code(self, code: int) -> 'EncapsulationPacketBuilder':
        """
        Sets the 'Length of Packet Length Field' code.
        -1: Dynamic (builder will determine based on fields and payload).
         0: PHL=1 octet (total packet length = 1, typically for Idle).
         1: PHL=2 octets (1 octet for length field).
         2: PHL=4 octets (2 octets for length field).
         3: PHL=8 octets (4 octets for length field).
        """
        if not (-1 <= code <= 3):
            raise ValueError("Length of Length code must be between -1 and 3.")
        self._length_of_length_code = code
        return self

    def set_data(self, data: bytes, offset: int = 0, length: int = -1) -> 'EncapsulationPacketBuilder':
        if length == -1:
            length = len(data) - offset
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("Invalid offset or length for data.")
        self._payload_unit = data[offset : offset + length]
        return self

    def clear_data(self) -> 'EncapsulationPacketBuilder':
        self._payload_unit = None
        return self

    def _compute_actual_header_length_and_code(self, payload_len: int) -> tuple[int, int]:
        """
        Determines the actual primary header length and its corresponding code (0-3)
        based on current field settings and payload length.
        """
        if self._length_of_length_code != -1: # User fixed it
            header_lengths = [1, 2, 4, 8]
            return header_lengths[self._length_of_length_code], self._length_of_length_code

        # Dynamic determination
        total_len_no_header = payload_len
        
        # Minimum header length is 1 (just first octet)
        # If only Protocol ID is needed and payload is 0, and total length is 1 (Idle) -> PHL=1
        if not self._protocol_id_ext_present and \
           not self._user_defined_field_present and \
           not self._ccsds_defined_field_present and \
           total_len_no_header == 0: # Implies an idle packet that fits in 1 byte
            # This is specific for an idle packet that is exactly 1 byte.
            # If protocol is IDLE and payload is 0, builder can choose PHL=1.
            if self._protocol_id == EncapsulationProtocolIdType.PROTOCOL_ID_IDLE and payload_len == 0:
                 return 1, 0 # PHL=1, code=0

        # Try PHL=2 (Length field is 1 byte, max total_len = 255)
        # Header needs: 1st octet + 1 octet for length.
        # Optional fields (ExtID, UserDef, CCSDSDef) cannot be present for PHL=2.
        if not self._protocol_id_ext_present and \
           not self._user_defined_field_present and \
           not self._ccsds_defined_field_present:
            if (2 + total_len_no_header) <= 255:
                return 2, 1 # PHL=2, code=1
        
        # Try PHL=4 (Length field is 2 bytes, max total_len = 65535)
        # Header needs: 1st octet + 2nd octet (for ExtID, UserDef) + 2 octets for length.
        # CCSDS-Defined field cannot be present for PHL=4.
        if not self._ccsds_defined_field_present:
             if (4 + total_len_no_header) <= 65535:
                # Ensure ExtID and UserDef are set if not explicitly, or clear them if not desired for PHL=4
                # If user set them, we respect that. If not, they are effectively 0.
                return 4, 2 # PHL=4, code=2

        # Default to PHL=8 (Length field is 4 bytes)
        # Header needs: 1st octet + 2nd octet + CCSDSDef (2B) + Length (4B)
        # All optional fields can be present.
        # Max total_len approx 4GB, well within limits for space.
        return 8, 3 # PHL=8, code=3


    def build(self) -> EncapsulationPacket:
        payload_bytes = self._payload_unit if self._payload_unit else b''
        payload_len = len(payload_bytes)

        actual_phl, lol_code = self._compute_actual_header_length_and_code(payload_len)
        
        total_packet_length = actual_phl + payload_len

        # Validate compatibility of chosen PHL with present fields
        if actual_phl < 4 and self._ccsds_defined_field_present:
            raise ValueError("CCSDS-Defined Field requires Primary Header Length of at least 4 (actually 8). Recalculated PHL is too small.")
        if actual_phl < 8 and self._ccsds_defined_field_present: # Strict check, CCSDS field is only in 8-byte header
            raise ValueError("CCSDS-Defined Field requires Primary Header Length of 8. Recalculated PHL is too small.")
        if actual_phl < 2 and (self._protocol_id_ext_present or self._user_defined_field_present):
            raise ValueError("Protocol ID Ext or User-Defined Field requires PHL of at least 2 (actually 4 or 8). Recalculated PHL is too small.")
        if actual_phl < 4 and (self._protocol_id_ext_present or self._user_defined_field_present): # Strict check, these are in 2nd octet, so PHL must be >=4 if they are to be included
            # If PHL is 2, 2nd octet is length. If PHL is 4 or 8, 2nd octet is UserDef/ExtID.
             pass # These fields are in the second octet, which is present for PHL >= 2.
                  # However, if PHL is 2, the second octet is length.
                  # So, if these are present, PHL must be >= 4.
            if actual_phl == 2 and (self._protocol_id_ext_present or self._user_defined_field_present):
                raise ValueError("Protocol ID Ext or User-Defined Field requires Primary Header Length of 4 or 8. PHL=2 is not sufficient.")


        header_buffer = bytearray(actual_phl)

        # Octet 0: Version (111), Protocol ID (3b), Length of Length code (2b)
        header_buffer[0] = (EncapsulationPacket.EP_VERSION << 5) | \
                           (self._protocol_id.value << 2) | \
                           lol_code
        
        if actual_phl == 1: # Idle packet, total length 1
            if total_packet_length != 1:
                raise ValueError(f"PHL=1 implies total length 1, but calculated {total_packet_length}")
            # No more fields to pack for PHL=1
        elif actual_phl == 2:
            # Octet 1: Packet Length (1 octet)
            if total_packet_length > 255:
                raise ValueError(f"Total packet length {total_packet_length} too large for PHL=2 (max 255).")
            header_buffer[1] = total_packet_length & 0xFF
        elif actual_phl == 4:
            # Octet 1: User-Defined Field (4b), Protocol ID Extension (4b)
            octet1 = 0
            if self._user_defined_field_present: octet1 |= (self._user_defined_field & 0x0F) << 4
            if self._protocol_id_ext_present: octet1 |= (self._protocol_id_ext & 0x0F)
            header_buffer[1] = octet1
            # Octets 2-3: Packet Length (2 octets)
            if total_packet_length > 65535:
                raise ValueError(f"Total packet length {total_packet_length} too large for PHL=4 (max 65535).")
            struct.pack_into(">H", header_buffer, 2, total_packet_length & 0xFFFF)
        elif actual_phl == 8:
            # Octet 1: User-Defined Field (4b), Protocol ID Extension (4b)
            octet1 = 0
            if self._user_defined_field_present: octet1 |= (self._user_defined_field & 0x0F) << 4
            if self._protocol_id_ext_present: octet1 |= (self._protocol_id_ext & 0x0F)
            header_buffer[1] = octet1
            # Octets 2-3: CCSDS-Defined Field (2 octets)
            if self._ccsds_defined_field_present and self._ccsds_defined_field:
                header_buffer[2:4] = self._ccsds_defined_field
            else: # If not present, field is 0
                header_buffer[2:4] = b'\x00\x00'
            # Octets 4-7: Packet Length (4 octets)
            # No practical limit for space applications, struct.pack handles Python int to 4 bytes.
            struct.pack_into(">I", header_buffer, 4, total_packet_length) 

        final_packet_data = bytes(header_buffer) + payload_bytes
        return EncapsulationPacket(final_packet_data, self._quality_indicator)


if __name__ == '__main__':
    # Example Usage
    builder = EncapsulationPacketBuilder.create()
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_LTP)
    builder.set_data(b"This is some LTP data.")
    # Dynamic header length will be chosen (likely PHL=2 or PHL=4)
    
    ep1 = builder.build()
    print(f"EP1 (dynamic PHL): {ep1}, HeaderLen: {ep1.primary_header_length}, Data: '{ep1.get_data_field_copy().decode()}'")

    builder.clear_data()
    builder.set_idle() # Sets ProtoID to IDLE, PHL to 1 (code 0)
    ep_idle = builder.build()
    print(f"EP Idle: {ep_idle}, HeaderLen: {ep_idle.primary_header_length}, IsIdle: {ep_idle.is_idle()}")
    assert ep_idle.primary_header_length == 1
    assert ep_idle.get_length() == 1

    builder.reset_to_defaults() # Assuming a helper if needed, or re-init
    builder = EncapsulationPacketBuilder.create() # Re-init
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_MISSION_SPECIFIC)
    builder.set_user_defined_field(0xA)
    builder.set_encapsulation_protocol_id_extension(0x5)
    builder.set_data(b"Payload for PHL=4")
    builder.set_length_of_length_code(2) # Force PHL=4
    ep_phl4 = builder.build()
    print(f"EP PHL4: {ep_phl4}, HeaderLen: {ep_phl4.primary_header_length}, UserDef: {hex(ep_phl4.user_defined_field)}, ExtID: {hex(ep_phl4.encapsulation_protocol_id_extension)}")
    assert ep_phl4.primary_header_length == 4

    builder = EncapsulationPacketBuilder.create()
    builder.set_encapsulation_protocol_id(EncapsulationProtocolIdType.PROTOCOL_ID_RESERVED_2)
    builder.set_user_defined_field(0x3)
    builder.set_encapsulation_protocol_id_extension(0x7)
    builder.set_ccsds_defined_field(b"\xAB\xCD")
    large_payload = b"A" * 200 # 200 bytes payload
    builder.set_data(large_payload)
    builder.set_length_of_length_code(3) # Force PHL=8
    ep_phl8 = builder.build()
    print(f"EP PHL8: {ep_phl8}, HeaderLen: {ep_phl8.primary_header_length}, CCSDSDef: {ep_phl8.ccsds_defined_field.hex()}")
    assert ep_phl8.primary_header_length == 8
    assert ep_phl8.encapsulated_data_field_length == 200
    assert ep_phl8.get_length() == 208

    # Test create from existing
    ep_from_existing_builder = EncapsulationPacketBuilder.create(initialiser=ep_phl8, copy_data_field=True)
    ep_rebuilt = ep_from_existing_builder.build()
    assert ep_rebuilt.get_packet() == ep_phl8.get_packet()
    print(f"EP Rebuilt from existing: {ep_rebuilt}, Data Len: {ep_rebuilt.encapsulated_data_field_length}")

    print("EncapsulationPacketBuilder tests completed.")

    # Add reset_to_defaults to builder for cleaner testing if this were a real test suite
    def reset_builder_for_testing(b):
        b._quality_indicator = True
        b._protocol_id = EncapsulationProtocolIdType.PROTOCOL_ID_IDLE
        b._protocol_id_ext_present = False
        b._protocol_id_ext = 0
        b._user_defined_field_present = False
        b._user_defined_field = 0
        b._ccsds_defined_field_present = False
        b._ccsds_defined_field = None
        b._length_of_length_code = -1 
        b._payload_unit = None
    EncapsulationPacketBuilder.reset_to_defaults = reset_builder_for_testing # Monkey patch for example
                                                                            # In real code, make it a method.
