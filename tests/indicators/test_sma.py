import unittest
from decimal import Decimal

from indicators import sma


class SmaTests(unittest.TestCase):
    def test_exact_decimal_sma(self):
        values = [Decimal("10.1"), Decimal("10.2"), Decimal("10.3")]
        self.assertEqual(sma(values, 3), Decimal("10.2"))

    def test_insufficient_history_returns_none(self):
        self.assertIsNone(sma([Decimal("10")], 2))

    def test_float_input_is_rejected(self):
        with self.assertRaises(TypeError):
            sma([Decimal("10"), 11.0], 2)


if __name__ == "__main__":
    unittest.main()
