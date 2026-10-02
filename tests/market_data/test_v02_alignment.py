from datetime import datetime,timezone
import unittest
from market_data.timeframes import is_timeframe_aligned


class AlignmentTests(unittest.TestCase):
    def test_fractional_millisecond_is_not_a_canonical_utc_bar_boundary(self):
        self.assertFalse(is_timeframe_aligned(datetime(2026,10,2,0,0,0,500,tzinfo=timezone.utc),'4h'))
        self.assertTrue(is_timeframe_aligned(datetime(2026,10,2,4,tzinfo=timezone.utc),'4h'))
