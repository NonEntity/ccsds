import unittest
import struct
from ccsds_tmtc_py.ocf.pdu.clcw import Clcw, CopEffectType
from ccsds_tmtc_py.ocf.pdu.abstract_ocf import AbstractOcf

class TestClcw(unittest.TestCase):
  def test_construct_and_parse(self):
    # CLCW: Vers=0,Type=0, Status=3, COP=COP1(01b), VCID=5, Res=0, NoRF=1,NoBL=0,Lockout=1,Wait=0,Retrans=1,FarmB=2,Report=0x42
    # Octet 0: Control Word Type (bit 7) = 0 (CLCW)
    #          Version (bits 6-5) = 00
    #          Status Field (bits 4-2) = 3 (011b)
    #          COP In Effect (bits 1-0) = COP1 (01b)
    #          Result: 0 00 011 01 = 0x0D
    byte0 = (0 << 7) | (0 << 5) | (3 << 2) | CopEffectType.COP1.value 
    self.assertEqual(byte0, 0x0D)

    # Octet 1: Virtual Channel ID (bits 7-2) = 5 (000101b)
    #          Reserved Spare (bits 1-0) = 0 (00b)
    #          Result: 000101 00 = 0x14
    byte1 = (5 << 2) | 0
    self.assertEqual(byte1, 0x14)

    # Octet 2: No RF Avail (bit 7) = 1
    #          No Bit Lock (bit 6) = 0
    #          Lockout (bit 5) = 1
    #          Wait (bit 4) = 0
    #          Retransmit (bit 3) = 1
    #          FARM-B Counter (bits 2-1) = 2 (10b)
    #          Spare (bit 0) = 0
    #          Result: 1 0 1 0 1 10 0 = 0xA8
    byte2 = (1 << 7) | (0 << 6) | (1 << 5) | (0 << 4) | (1 << 3) | (2 << 1) | 0
    self.assertEqual(byte2, 0xA8)
    
    byte3 = 0x42 # Report Value

    clcw_bytes = bytes([byte0, byte1, byte2, byte3])
    clcw = Clcw(clcw_bytes)
    
    self.assertEqual(clcw.version_number, 0)
    self.assertTrue(clcw.is_clcw) # From AbstractOcf
    self.assertEqual(clcw.status_field, 3)
    self.assertEqual(clcw.cop_in_effect, CopEffectType.COP1)
    self.assertEqual(clcw.virtual_channel_id, 5)
    self.assertEqual(clcw.reserved_spare1, 0)
    self.assertTrue(clcw.no_rf_available_flag)
    self.assertFalse(clcw.no_bitlock_flag)
    self.assertTrue(clcw.lockout_flag)
    self.assertFalse(clcw.wait_flag)
    self.assertTrue(clcw.retransmit_flag)
    self.assertEqual(clcw.farm_b_counter, 2)
    self.assertEqual(clcw.report_value, 0x42)
    self.assertEqual(len(clcw), 4) # Test __len__

  def test_invalid_length(self):
    with self.assertRaisesRegex(ValueError, "CLCW data must be 4 bytes long"):
      Clcw(b"\x00\x00\x00") # Too short
    with self.assertRaisesRegex(ValueError, "CLCW data must be 4 bytes long"):
      Clcw(b"\x00\x00\x00\x00\x00") # Too long

  def test_not_clcw_type(self):
    # Set Control Word Type bit (MSB of first octet) to 1
    not_clcw_bytes = b"\x80\x00\x00\x00" 
    with self.assertRaisesRegex(ValueError, "OCF data is not a CLCW"):
      Clcw(not_clcw_bytes)
      
  def test_invalid_clcw_version(self):
    # Version = 1 (01b at bits 6-5 of first octet)
    # Control Word Type = 0, Version = 01, Status = 0, COP = 0
    # 0 01 000 00 = 0x20
    invalid_version_bytes = b"\x20\x00\x00\x00"
    with self.assertRaisesRegex(ValueError, "Invalid CLCW version number"):
      Clcw(invalid_version_bytes)

class TestAbstractOcf(unittest.TestCase):
    def test_abstract_ocf_properties(self):
        clcw_valid_data = b"\x0D\x14\xA8\x42" # Valid CLCW
        abs_ocf_clcw = AbstractOcf(clcw_valid_data)
        self.assertTrue(abs_ocf_clcw.is_clcw)
        self.assertEqual(abs_ocf_clcw.ocf, clcw_valid_data)

        reserved_ocf_data = b"\x80\x00\x00\x00" # Type bit is 1 (Reserved)
        abs_ocf_reserved = AbstractOcf(reserved_ocf_data)
        self.assertFalse(abs_ocf_reserved.is_clcw)
        self.assertEqual(abs_ocf_reserved.ocf, reserved_ocf_data)
        self.assertEqual(len(abs_ocf_reserved), 4)

    def test_abstract_ocf_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "OCF data cannot be None or empty."):
            AbstractOcf(None) # type: ignore
        with self.assertRaisesRegex(ValueError, "OCF data cannot be None or empty."):
            AbstractOcf(b"")

if __name__ == '__main__':
    unittest.main()
