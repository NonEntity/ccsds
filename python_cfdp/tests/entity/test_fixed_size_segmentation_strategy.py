import os
import tempfile
import unittest

from python_cfdp.entity.segmenters.impl import FixedSizeSegmentationStrategy


class DummyFilestore:
    def __init__(self, root: str):
        self.root = root

    def read_file(self, path: str):
        return open(os.path.join(self.root, path), "rb")


class FakeRemoteEntity:
    def __init__(self, max_len: int):
        self._len = max_len

    def get_maximum_file_segment_length(self):
        return self._len


class FakeMib:
    def __init__(self, max_len: int):
        self._remote = FakeRemoteEntity(max_len)

    def get_remote_entity_by_id(self, _):
        return self._remote


class TestFixedSizeSegmentationStrategy(unittest.TestCase):
    def test_fixed_segmentation_strategy(self):
        strategy = FixedSizeSegmentationStrategy()
        self.assertTrue(strategy.support(None, None, "whatever"))

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.bin")
            with open(path, "wb") as f:
                f.write(b"data")

            seg = strategy.new_segmenter(FakeMib(512), DummyFilestore(tmpdir), "test.bin", 1)
            self.assertIsNotNone(seg)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
