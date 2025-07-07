import unittest
from python_cfdp.entity.segmenters import FileSegment, RCS_NO_START_END


class TestFileSegment(unittest.TestCase):
    def test_file_segment_creation(self):
        eof = FileSegment.eof_segment()
        self.assertTrue(eof.eof)
        self.assertIsNone(eof.data)
        self.assertIsNotNone(str(eof))

        seg = FileSegment(100, b"\x01\x02\x03", b"\x00", RCS_NO_START_END)
        self.assertEqual(seg.offset, 100)
        self.assertEqual(seg.data, b"\x01\x02\x03")
        self.assertEqual(seg.metadata, b"\x00")
        self.assertEqual(seg.record_continuation_state, RCS_NO_START_END)
        self.assertFalse(seg.eof)
        self.assertIsNotNone(str(seg))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
