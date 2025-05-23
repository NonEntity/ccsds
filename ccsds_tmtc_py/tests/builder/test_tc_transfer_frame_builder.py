import unittest
import struct
from ccsds_tmtc_py.datalink.builder.tc_transfer_frame_builder import TcTransferFrameBuilder
from ccsds_tmtc_py.datalink.pdu.tc_transfer_frame import TcTransferFrame, FrameType, ControlCommandType, SequenceFlagType as TcFrameSequenceFlagType
from ccsds_tmtc_py.datalink.pdu.abstract_transfer_frame import IllegalStateException

class TestTcTransferFrameBuilder(unittest.TestCase):
  def test_build_ad_frame_no_opt(self):
    builder = TcTransferFrameBuilder.create(fecf_present=False)
    builder.set_spacecraft_id(0xCD).set_virtual_channel_id(4).set_frame_sequence_number(50)
    builder.set_bypass_flag(False).set_control_command_flag(False) # AD Frame
    
    payload = b"AD_Frame_Data"
    builder.add_data(payload)
    
    tc_frame_pdu = builder.build()
    
    # The segmented_fn for TcTransferFrame PDU is to tell it if it *should* parse a seg_hdr
    # The builder itself decides whether to *include* one.
    reparsed = TcTransferFrame(tc_frame_pdu.get_frame(), lambda vc_id: False, fecf_present=False, security_header_length=0, security_trailer_length=0)
    
    self.assertEqual(reparsed.spacecraft_id, 0xCD)
    self.assertEqual(reparsed.virtual_channel_id, 4)
    self.assertEqual(reparsed.virtual_channel_frame_count, 50) # VCFC from frame_sequence_number
    self.assertFalse(reparsed.bypass_flag)
    self.assertFalse(reparsed.control_command_flag)
    self.assertEqual(reparsed.frame_type, FrameType.AD)
    self.assertFalse(reparsed.segmented)
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_build_bc_frame_unlock_with_fecf(self):
    builder = TcTransferFrameBuilder.create(fecf_present=True)
    builder.set_spacecraft_id(0xEF).set_virtual_channel_id(1).set_frame_sequence_number(10)
    builder.set_control_command_flag(True) # BC Frame
    builder.set_unlock_control_command() # Sets payload to b"\x00"
    
    tc_frame_pdu = builder.build()
    
    reparsed = TcTransferFrame(tc_frame_pdu.get_frame(), lambda vc_id: False, fecf_present=True, security_header_length=0, security_trailer_length=0)
    self.assertTrue(reparsed.control_command_flag)
    self.assertEqual(reparsed.frame_type, FrameType.BC)
    self.assertEqual(reparsed.control_command_type, ControlCommandType.UNLOCK)
    self.assertTrue(reparsed.is_fecf_present())
    self.assertEqual(reparsed.get_fecf(), 0) # Placeholder CRC is 0

  def test_build_bd_frame_segmented_security(self):
    seg_map_id = 0x1A
    seg_seq_flag = TcFrameSequenceFlagType.CONTINUE
    sec_hdr = b"SHEAD"
    sec_trl = b"STRAIL"
    payload = b"Segmented_BD_Data"

    builder = TcTransferFrameBuilder.create(fecf_present=False)
    builder.set_bypass_flag(True).set_control_command_flag(False) # BD Frame
    builder.set_segment(map_id=seg_map_id, sequence_flag=seg_seq_flag)
    builder.set_security(header=sec_hdr, trailer=sec_trl)
    builder.add_data(payload)
    
    # Set other required fields
    builder.set_spacecraft_id(0x11).set_virtual_channel_id(2).set_frame_sequence_number(33)

    tc_frame_pdu = builder.build()
    reparsed = TcTransferFrame(tc_frame_pdu.get_frame(), 
                               lambda vc_id: True, # segmented_fn indicates seg hdr is expected by parser
                               fecf_present=False, 
                               security_header_length=len(sec_hdr), 
                               security_trailer_length=len(sec_trl))
    
    self.assertTrue(reparsed.bypass_flag)
    self.assertEqual(reparsed.frame_type, FrameType.BD)
    self.assertTrue(reparsed.segmented)
    self.assertEqual(reparsed.map_id, seg_map_id)
    self.assertEqual(reparsed.sequence_flag, seg_seq_flag)
    self.assertEqual(reparsed.get_security_header_copy(), sec_hdr)
    self.assertEqual(reparsed.get_security_trailer_copy(), sec_trl)
    self.assertEqual(reparsed.get_data_field_copy(), payload)

  def test_set_vr_control_command(self):
    builder = TcTransferFrameBuilder.create(fecf_present=False)
    builder.set_control_command_flag(True)
    builder.set_set_vr_control_command(fs_number=0x7F)
    tc_frame_pdu = builder.build()
    reparsed = TcTransferFrame(tc_frame_pdu.get_frame(), lambda vc_id: False, False,0,0)
    self.assertEqual(reparsed.control_command_type, ControlCommandType.SET_VR)
    self.assertEqual(reparsed.set_vr_value, 0x7F)
    self.assertEqual(reparsed.get_data_field_copy(), b"\x82\x00\x7F")

  def test_build_error_payload_not_set_ad_bd(self):
    builder_ad = TcTransferFrameBuilder.create(fecf_present=False).set_control_command_flag(False).set_bypass_flag(False) # AD
    with self.assertRaisesRegex(IllegalStateException, "Payload data not set for AD/BD frame"):
        builder_ad.build()
        
    builder_bd = TcTransferFrameBuilder.create(fecf_present=False).set_control_command_flag(False).set_bypass_flag(True) # BD
    builder_bd.set_segment(0, TcFrameSequenceFlagType.FIRST) # Need to set segment if BD might imply it
    with self.assertRaisesRegex(IllegalStateException, "Payload data not set for AD/BD frame"):
        builder_bd.build()

  def test_segmentation_on_bc_error(self):
    builder = TcTransferFrameBuilder.create(fecf_present=False)
    builder.set_control_command_flag(True) # BC Frame
    with self.assertRaisesRegex(IllegalStateException, "Segmentation is not applicable to BC"):
        builder.set_segment(map_id=1, sequence_flag=TcFrameSequenceFlagType.FIRST)

  def test_security_on_bc_error(self):
    builder = TcTransferFrameBuilder.create(fecf_present=False)
    builder.set_control_command_flag(True) # BC Frame
    with self.assertRaisesRegex(IllegalStateException, "Security header/trailer is not supported for BC frames"):
        builder.set_security(header=b"sec", trailer=None)


if __name__ == '__main__':
    unittest.main()
