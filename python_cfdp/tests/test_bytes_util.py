import unittest

from python_cfdp.common import (
    read_integer,
    encode_integer,
    write_lv_string,
    read_lv_string,
    get_encoding_octets_nb,
)

class TestBytesUtil(unittest.TestCase):
    def test_integer_roundtrip(self):
        value = 0xABCD
        enc = encode_integer(value, 2)
        self.assertEqual(enc, b'\xab\xcd')
        self.assertEqual(read_integer(enc, 0, 2), value)

    def test_lv_string(self):
        buf = bytearray()
        write_lv_string(buf, "CFDP")
        self.assertEqual(buf, b"\x04CFDP")
        self.assertEqual(read_lv_string(bytes(buf), 0), "CFDP")

    def test_encoding_octets(self):
        self.assertEqual(get_encoding_octets_nb(0), 1)
        self.assertEqual(get_encoding_octets_nb(255), 1)
        self.assertEqual(get_encoding_octets_nb(256), 2)

if __name__ == "__main__":
    unittest.main()
