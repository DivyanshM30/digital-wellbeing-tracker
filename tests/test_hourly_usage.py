"""Hourly storage regression tests; only temporary files are used."""
from datetime import datetime
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import test_daily_usage as daily

class HourlyUsageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'daily_usage.json'
        self.store = daily.Store(self.path)
        self.now = datetime(2026, 9, 28, 15)

    def view(self, day='2026-09-27', hour=None, store=None):
        return (store or self.store).hourly_history(day, hour, self.now)

    def test_hour_boundary_split_and_restart(self):
        self.store.record('editor.exe', datetime(2026, 9, 27, 10, 59, 50).timestamp(), 30)
        reopened = daily.Store(self.path)
        self.assertEqual(self.view(hour=10, store=reopened)['apps'], {'editor.exe': 10})
        self.assertEqual(self.view(hour=11, store=reopened)['apps'], {'editor.exe': 20})
        self.assertEqual(reopened.usage('2026-09-27'), {'editor.exe': 30})
        self.assertEqual(self.view(store=reopened)['unallocated'], 0)

    def test_midnight_and_multiple_hours_preserve_totals(self):
        self.store.record('editor.exe', datetime(2026, 9, 27, 23, 59, 50).timestamp(), 7220)
        self.assertEqual(self.view(hour=23)['apps'], {'editor.exe': 10})
        self.assertEqual(self.view('2026-09-28', 0)['apps'], {'editor.exe': 3600})
        self.assertEqual(self.view('2026-09-28', 1)['apps'], {'editor.exe': 3600})
        self.assertEqual(self.view('2026-09-28', 2)['apps'], {'editor.exe': 10})
        self.assertEqual(sum(row['duration'] for row in self.store.rows()), 7220)

    def test_old_history_is_read_only_until_first_write_and_backed_up(self):
        original = json.dumps({'version': 1, 'days': {'2026-09-27': {'editor.exe': 900}},
                               'recovered_days': ['2026-09-27']}).encode()
        self.path.write_bytes(original)
        self.store = daily.Store(self.path)
        self.assertEqual(self.view()['unallocated'], 900)
        self.assertEqual(self.view()['apps'], {})
        self.assertEqual(self.path.read_bytes(), original)
        self.store.record('editor.exe', datetime(2026, 9, 27, 12).timestamp(), 60)
        self.assertEqual(self.path.with_name('daily_usage.before-hourly-v2.json').read_bytes(), original)
        self.assertEqual(json.loads(self.path.read_bytes())['version'], 2)
        self.assertEqual(self.view()['daily_total'], 960)
        self.assertEqual(self.view()['unallocated'], 900)
        self.assertEqual(daily.Store(self.path).recovered_days, ['2026-09-27'])

    def test_failed_replace_rolls_back_both_maps_and_retry_counts_once(self):
        start = datetime(2026, 9, 27, 12).timestamp()
        self.store.record('editor.exe', start, 60)
        before = self.path.read_bytes()
        with patch.object(os, 'replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                self.store.record('editor.exe', start + 60, 30)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.view()['daily_total'], 60)
        self.assertEqual(self.view()['detailed_total'], 60)
        self.assertEqual(list(self.path.parent.glob('.daily-*.tmp')), [])
        self.store.record('editor.exe', start + 60, 30)
        self.assertEqual(self.view(store=daily.Store(self.path))['detailed_total'], 90)

    def test_invalid_hourly_payload_is_never_overwritten(self):
        for hours in (None, {'2026-09-27': {'24': {'a': 1}}},
                      {'2026-09-27': {'1': {'a': -1}}},
                      {'2026-09-27': {'1': {'a': 11}}},
                      {'2026-09-27': {'1': {'a': float('nan')}}}):
            with self.subTest(hours=hours):
                original = json.dumps({'version': 2, 'days': {'2026-09-27': {'a': 10}}, 'hours': hours})
                self.path.write_text(original)
                with self.assertRaises(ValueError):
                    daily.Store(self.path)
                self.assertEqual(self.path.read_text(), original)

    def test_empty_future_and_hour_selection(self):
        view = self.view('2026-09-28')
        self.assertEqual(len(view['chart']), 24)
        self.assertFalse(view['chart'][15]['future'])
        self.assertTrue(view['chart'][16]['future'])
        self.assertEqual(view['apps'], {})
        for hour in (-1, 24, '12'):
            with self.assertRaises(ValueError):
                self.view(hour=hour)
        with self.assertRaises(ValueError):
            self.view('2026-09-29')

    def test_reads_return_detached_snapshots_and_rank_all_apps(self):
        start = datetime(2026, 9, 27, 12).timestamp()
        self.store.record('small', start, 10)
        self.store.record('large', start + 10, 20)
        before = self.path.read_bytes()
        view = self.view(hour=12)
        self.assertEqual(list(view['apps']), ['large', 'small'])
        view['chart'][12]['apps']['large'] = 999
        self.assertEqual(self.view(hour=12)['apps']['large'], 20)
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_recovery_preserves_existing_hourly_data(self):
        self.store.record('editor.exe', datetime(2026, 9, 27, 12).timestamp(), 60)
        logs = self.path.parent / 'logs'
        logs.mkdir()
        (logs / '2026-09-26.log').write_text('12:00:00 | editor.exe | Old window | 90s\n')
        self.store.recover_legacy_logs(logs, self.now.date())
        reopened = daily.Store(self.path)
        self.assertEqual(self.view(store=reopened)['detailed_total'], 60)
        self.assertEqual(self.view('2026-09-26', store=reopened)['unallocated'], 90)

    def test_idle_cutoff_and_suspend_gap_do_not_fill_hours(self):
        self.start = datetime(2026, 9, 27, 12, 59, 59).timestamp()
        tracker = daily.DailyUsageTests.tracker(self)
        with patch.object(daily.time, 'monotonic', return_value=102), patch.object(daily.time, 'time', return_value=self.start + 2):
            tracker.log_app_usage('editor.exe', 'Document', (60.5, True))
        with patch.object(daily.time, 'monotonic', return_value=3702), patch.object(daily.time, 'time', return_value=self.start + 3602):
            tracker.log_app_usage('editor.exe', 'Document', (0, True))
        with patch.object(daily.time, 'monotonic', return_value=3703), patch.object(daily.time, 'time', return_value=self.start + 3603):
            tracker.log_app_usage('editor.exe', 'Document', (0, True))
        self.assertEqual(self.view(hour=12)['apps'], {'editor.exe': 1})
        self.assertEqual(self.view(hour=13)['apps'], {'editor.exe': .5})
        self.assertEqual(self.view(hour=14)['apps'], {'editor.exe': 1})
        self.assertEqual(self.view()['detailed_total'], 2.5)

    def test_failed_upgrade_preserves_v1_and_backup(self):
        original = json.dumps({'version': 1, 'days': {'2026-09-27': {'a': 90}}}).encode()
        self.path.write_bytes(original)
        self.store = daily.Store(self.path)
        with patch.object(os, 'replace', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                self.store.record('a', datetime(2026, 9, 27, 12).timestamp(), 5)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.store.storage_version, 1)
        self.assertEqual(self.store.hours, {})
        self.assertEqual(self.path.with_name('daily_usage.before-hourly-v2.json').read_bytes(), original)
