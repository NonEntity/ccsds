import os
import tempfile
import unittest

from python_cfdp.entity.segmenters.impl import FixedSizeSegmenter


class DummyFilestore:
    def __init__(self, root: str):
        self.root = root

    def read_file(self, path: str):
        return open(os.path.join(self.root, path), "rb")


class TestFixedSizeSegmenter(unittest.TestCase):
    def test_fixed_size_segmenter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.bin")
            with open(path, "wb") as f:
                f.write(os.urandom(1024 * 10))

            seg = FixedSizeSegmenter(DummyFilestore(tmpdir), "test.bin", 512)

            count = 0
            while True:
                chunk = seg.next_segment()
                if chunk.eof:
                    break
                count += 1

            self.assertEqual(count, 20)
            self.assertTrue(seg.next_segment().eof)
            self.assertTrue(seg.next_segment().eof)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
