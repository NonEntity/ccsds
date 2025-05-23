import unittest
from ccsds_tmtc_py.ocf.builder.clcw_builder import ClcwBuilder
from ccsds_tmtc_py.ocf.pdu.clcw import Clcw, CopEffectType

class TestClcwBuilder(unittest.TestCase):
  def test_build_clcw_default_values(self):
    builder = ClcwBuilder.create()
    clcw_pdu = builder.build() # Uses Clcw(clcw_bytes) internally
    
    # Default CLCW has version 0, type 0 (CLCW), all other fields 0/False
    # The Clcw PDU parser will validate version and type.
    self.assertEqual(clcw_pdu.status_field, 0)
    self.assertEqual(clcw_pdu.cop_in_effect, CopEffectType.NONE)
    self.assertEqual(clcw_pdu.virtual_channel_id, 0)
    self.assertEqual(clcw_pdu.reserved_spare1, 0)
    self.assertFalse(clcw_pdu.no_rf_available_flag)
    self.assertFalse(clcw_pdu.no_bitlock_flag)
    self.assertFalse(clcw_pdu.lockout_flag)
    self.assertFalse(clcw_pdu.wait_flag)
    self.assertFalse(clcw_pdu.retransmit_flag)
    self.assertEqual(clcw_pdu.farm_b_counter, 0)
    self.assertEqual(clcw_pdu.report_value, 0)
    
    # Verify raw bytes for all defaults (00000000)
    self.assertEqual(clcw_pdu.ocf, b'\x00\x00\x00\x00')

  def test_build_clcw_all_fields_set(self):
    builder = ClcwBuilder.create()
    builder.set_status_field(3)
    builder.set_cop_in_effect(CopEffectType.COP1)
    builder.set_virtual_channel_id(5)
    builder.set_reserved_spare(1) # 01b
    builder.set_no_rf_available_flag(True)
    builder.set_no_bitlock_flag(False)
    builder.set_lockout_flag(True)
    builder.set_wait_flag(False)
    builder.set_retransmit_flag(True)
    builder.set_farm_b_counter(2) # 10b
    builder.set_report_value(0xAB)
    
    clcw_pdu = builder.build()

    # Expected bytes based on TestClcw PDU test:
    # Octet 0: Vers=0,Type=0, Status=3(011), COP=COP1(01) -> 00001101 = 0x0D
    # Octet 1: VCID=5(000101), Res=1(01) -> 00010101 = 0x15
    # Octet 2: NoRF=1,NoBL=0,Lockout=1,Wait=0,Retrans=1,FarmB=2(10),Spare=0 -> 10101100 = 0xAC
    # Octet 3: Report=0xAB
    expected_bytes = bytes([0x0D, 0x15, 0xAC, 0xAB])
    self.assertEqual(clcw_pdu.ocf, expected_bytes)

    # Also verify fields through PDU properties
    self.assertEqual(clcw_pdu.status_field, 3)
    self.assertEqual(clcw_pdu.cop_in_effect, CopEffectType.COP1)
    self.assertEqual(clcw_pdu.virtual_channel_id, 5)
    self.assertEqual(clcw_pdu.reserved_spare1, 1)
    self.assertTrue(clcw_pdu.no_rf_available_flag)
    self.assertFalse(clcw_pdu.no_bitlock_flag)
    self.assertTrue(clcw_pdu.lockout_flag)
    self.assertFalse(clcw_pdu.wait_flag)
    self.assertTrue(clcw_pdu.retransmit_flag)
    self.assertEqual(clcw_pdu.farm_b_counter, 2)
    self.assertEqual(clcw_pdu.report_value, 0xAB)

  def test_set_cop1_in_effect_helper(self):
    builder = ClcwBuilder.create()
    builder.set_cop1_in_effect(True)
    self.assertEqual(builder.build().cop_in_effect, CopEffectType.COP1)
    builder.set_cop1_in_effect(False)
    self.assertEqual(builder.build().cop_in_effect, CopEffectType.NONE)

if __name__ == '__main__':
    unittest.main()
