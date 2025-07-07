import unittest

from python_cfdp.entity.indication import FaultIndication
from python_cfdp.entity import ConditionCode


class TestFaultIndication(unittest.TestCase):
    def test_fault_indication_construction(self):
        fi = FaultIndication(
            transaction_id=3,
            condition_code=ConditionCode.CC_CANCEL_REQUEST_RECEIVED,
            progress=2321,
        )
        self.assertEqual(fi.transaction_id, 3)
        self.assertEqual(fi.condition_code, ConditionCode.CC_CANCEL_REQUEST_RECEIVED)
        self.assertEqual(fi.progress, 2321)
        self.assertIsNone(fi.status_report)
        self.assertIn("FaultIndication", str(fi))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
