"""Weekly comparisons must preserve storage and expose missing coverage."""
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest

import test_daily_usage as daily


class WeeklyComparisonTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / 'usage.json'
        self.store = daily.Store(self.path)

    def week(self, monday, count, apps):
        for offset in range(count):
            day = (datetime.fromisoformat(monday) + timedelta(days=offset)).date().isoformat()
            self.store.days[day] = apps.copy()

    def test_full_week_totals_averages_ranking_and_delta(self):
        self.week('2026-09-07', 7, {'a.exe': 60})
        self.week('2026-09-14', 7, {'a.exe': 60, 'b.exe': 120})
        result = self.store.weekly_comparison('2026-09-16', today=datetime(2026, 9, 22).date())
        self.assertEqual(result['total'], 1260)
        self.assertEqual(result['average'], 180)
        self.assertEqual(result['previous_average'], 60)
        self.assertEqual(result['percent'], 200)
        self.assertEqual(result['delta'], 840)
        self.assertEqual(next(iter(result['current']['apps'])), 'b.exe')
        self.assertFalse(result['partial'])

    def test_week_so_far_uses_same_number_of_days_and_flags_today(self):
        self.week('2026-09-07', 7, {'a.exe': 120})
        self.week('2026-09-14', 3, {'a.exe': 60})
        result = self.store.weekly_comparison('2026-09-14', today=datetime(2026, 9, 16).date())
        self.assertEqual(result['previous_end'], '2026-09-09')
        self.assertEqual(result['previous_total'], 360)
        self.assertEqual(result['percent'], -50)
        self.assertTrue(result['partial'])

    def test_missing_days_do_not_claim_a_reduction(self):
        self.week('2026-09-07', 7, {'a.exe': 120})
        self.week('2026-09-14', 6, {'a.exe': 60})
        result = self.store.weekly_comparison('2026-09-14', today=datetime(2026, 9, 22).date())
        self.assertFalse(result['coverage_complete'])
        self.assertIsNone(result['percent'])
        self.assertIsNone(result['delta'])
        self.assertEqual(result['current']['recorded'], 6)

    def test_no_previous_history_or_zero_baseline_has_no_percentage(self):
        self.week('2026-09-14', 7, {'a.exe': 60})
        result = self.store.weekly_comparison('2026-09-14', today=datetime(2026, 9, 22).date())
        self.assertIsNone(result['percent'])
        self.assertEqual(result['previous_recorded'], 0)
        self.week('2026-09-07', 7, {'a.exe': 0})
        result = self.store.weekly_comparison('2026-09-14', today=datetime(2026, 9, 22).date())
        self.assertTrue(result['coverage_complete'])
        self.assertIsNone(result['percent'])
        self.assertEqual(result['delta'], 420)

    def test_app_filter_compares_the_same_app(self):
        self.week('2026-09-07', 7, {'a.exe': 60, 'b.exe': 500})
        self.week('2026-09-14', 7, {'a.exe': 60})
        result = self.store.weekly_comparison('2026-09-14', today=datetime(2026, 9, 22).date(), app='a.exe')
        self.assertEqual(result['percent'], 0)
        self.assertEqual(result['total'], 420)

    def test_year_boundary_recovery_and_read_only_storage(self):
        self.week('2020-12-28', 7, {'a.exe': 60})
        self.week('2021-01-04', 7, {'a.exe': 120})
        self.store.commit(self.store.days, ['2020-12-29'])
        before = self.path.read_bytes()
        result = self.store.weekly_comparison('2021-01-04', today=datetime(2021, 1, 12).date())
        self.assertEqual(result['previous_start'], '2020-12-28')
        self.assertEqual(result['previous_end'], '2021-01-03')
        self.assertTrue(result['recovered'])
        self.assertEqual(self.path.read_bytes(), before)

    def test_future_date_rejected(self):
        with self.assertRaises(ValueError):
            self.store.weekly_comparison('2026-09-28', today=datetime(2026, 9, 27).date())
