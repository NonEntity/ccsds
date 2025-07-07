# Ensure bundled third-party modules are importable
import os
import sys

_VENDOR_DIR = os.path.join(os.path.dirname(__file__), "..", "vendor")
if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)

# This file marks ccsds_tmtc_py as a Python package.
