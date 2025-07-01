# -*- coding: utf-8 -*-
"""Utility functions for working with byte arrays.

This module provides Python equivalents of the helper methods in
`eu.dariolucia.ccsds.cfdp.common.BytesUtil`.
"""
from typing import Optional
from .cfdp_runtime_exception import CfdpRuntimeException
# Constants for get_encoding_octets_nb
BYTE_LIMITS = [
    (1, (256 ** 1) - 1),
    (2, (256 ** 2) - 1),
    (3, (256 ** 3) - 1),
    (4, (256 ** 4) - 1),
    (5, (256 ** 5) - 1),
    (6, (256 ** 6) - 1),
    (7, (256 ** 7) - 1),
]


def read_integer(data: bytes, offset: int, size: int) -> Optional[int]:
    """Read an unsigned integer from ``data`` starting at ``offset``.

    ``size`` specifies the number of bytes to read. When ``size`` is ``0`` a
    ``None`` value is returned.
    """
    if size > 8:
        raise CfdpRuntimeException(
            f"Cannot read an unsigned integer larger than 8, actual is {size}")
    if size < 0:
        raise CfdpRuntimeException(
            f"Cannot read an unsigned integer with a negative size, actual is {size}")
    if size == 0:
        return None
    value = 0
    for i in range(size):
        value <<= 8
        value |= data[offset + i] & 0xFF
    return value


def encode_integer(value: int, size: int) -> bytes:
    """Encode ``value`` to ``size`` bytes using big endian order."""
    if size > 8:
        raise CfdpRuntimeException(
            f"Cannot encode an unsigned integer larger than 8, actual is {size}")
    if size < 0:
        raise CfdpRuntimeException(
            f"Cannot encode an unsigned integer with a negative size, actual is {size}")
    output = bytearray(size)
    mask = 0xFF
    for i in range(size):
        output[size - 1 - i] = (value & mask) >> (8 * i)
        mask <<= 8
    return bytes(output)


def write_lv_string(buf: bytearray, string: Optional[str]) -> None:
    """Write a LV (length-value) string to ``buf`` using ASCII encoding."""
    if string and len(string) > 255:
        raise ValueError(
            f"String length is greater than 255, cannot write LV string: {string}")
    if string:
        buf.append(len(string) & 0xFF)
        buf.extend(string.encode('ascii'))
    else:
        buf.append(0)


def read_lv_string(data: bytes, offset: int) -> str:
    """Read a LV (length-value) string from ``data`` starting at ``offset``."""
    length = data[offset] & 0xFF
    if length:
        return data[offset + 1: offset + 1 + length].decode('ascii')
    return ""


def get_encoding_octets_nb(max_value: int) -> int:
    """Return the minimum number of bytes required to encode ``max_value``."""
    if max_value < 0:
        return 8
    if max_value == 0:
        return 1
    for bytes_nb, limit in BYTE_LIMITS:
        if max_value <= limit:
            return bytes_nb
    return 8
