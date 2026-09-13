"""Persistence checks using temporary files; no monitoring or personal data."""
import ast
from collections import defaultdict
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import queue
import re
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text(encoding='utf-8'))
namespace = dict(Path=Path, threading=threading, datetime=datetime, timedelta=timedelta,
                 tempfile=tempfile, math=math, json=json, os=os, time=time, queue=queue,
                 sys=sys, re=re, defaultdict=defaultdict, __file__=str(Path(__file__).resolve().parents[1] / 'main.py'))
classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
exec(compile(ast.Module(body=classes, type_ignores=[]), 'main.py', 'exec'), namespace)
Store = namespace['DailyUsageStore']
Tracker = namespace['ScreenTimeTracker']
App = namespace['DigitalWellnessApp']


class DailyUsageTests(unittest.TestCase):
    def test_legacy_recovery_preserves_existing_days_and_is_idempotent(self):
        logs = Path(self.temporary.name) / 'logs'
        logs.mkdir()
        (logs / '2026-09-11.log').write_bytes(b'12:00:00 | a.exe | Title \xb7 private | 3600.50s\n')
        (logs / '2026-09-12.log').write_text('12:00:00 | a.exe | Title | 999s\n')
        (logs / '2026-09-13.log').write_text('12:00:00 | a.exe | Title | 999s\n')
        self.store.record('existing.exe', self.start, 60)
        before = self.path.read_bytes()
        result = self.store.recover_legacy_logs(logs, today=datetime(2026, 9, 13).date())
        self.assertEqual(result, ['2026-09-11'])
        self.assertEqual(self.store.usage('2026-09-11'), {'a.exe': 3600.5})
        self.assertEqual(self.store.usage('2026-09-12'), {'existing.exe': 60})
        self.assertEqual(self.store.usage('2026-09-13'), {})
        self.assertEqual((self.path.parent / 'daily_usage.before-legacy-import.json').read_bytes(), before)
        reopened = Store(self.path)
        self.assertEqual(reopened.recover_legacy_logs(logs, today=datetime(2026, 9, 13).date()), [])
        self.assertEqual(reopened.recovered_days, ['2026-09-11'])

    def test_legacy_recovery_skips_malformed_and_impossible_logs(self):
        logs = Path(self.temporary.name) / 'logs'
        logs.mkdir()
        (logs / '2026-09-10.log').write_text('12:00:00 | a.exe | Title | 20s\nbad line')
        (logs / '2026-09-11.log').write_text('99:00:00 | a.exe | Title | 20s')
        (logs / '2026-09-12.log').write_text('12:00:00 | a.exe | Title | 90000s')
        self.assertEqual(self.store.recover_legacy_logs(logs, today=datetime(2026, 9, 13).date()), [])
        self.assertFalse(self.path.exists())

    def test_weekly_history_includes_all_apps_and_elapsed_days(self):
        for index in range(8):
            self.store.record(f'app{index}.exe', datetime(2026, 9, 7, 12).timestamp(), 60)
        self.store.record('app0.exe', datetime(2026, 9, 9, 12).timestamp(), 120)
        result = self.store.history('2026-09-09', weekly=True, today=datetime(2026, 9, 9).date())
        self.assertEqual(result['start'], '2026-09-07')
        self.assertEqual(result['end'], '2026-09-09')
        self.assertEqual((result['days'], result['recorded']), (3, 2))
        self.assertEqual(len(result['apps']), 8)
        self.assertEqual(sum(result['apps'].values()), 600)
        self.assertEqual(result['apps']['app0.exe'], 180)
        self.assertFalse(result['chart'][1]['recorded'])
        self.assertTrue(result['chart'][3]['future'])

    def test_daily_history_does_not_include_other_days_in_total(self):
        self.store.record('a.exe', self.start, 60)
        self.store.record('a.exe', self.start - 86400, 120)
        result = self.store.history('2026-09-12', today=datetime(2026, 9, 13).date())
        self.assertEqual(result['apps'], {'a.exe': 60})
        self.assertEqual(result['days'], 1)

    def test_week_crosses_year_boundary_and_includes_sunday(self):
        result = self.store.history('2027-01-03', weekly=True, today=datetime(2027, 1, 4).date())
        self.assertEqual((result['start'], result['end'], result['days']), ('2026-12-28', '2027-01-03', 7))

    def test_empty_history_and_invalid_date(self):
        result = self.store.history('2026-09-12', today=datetime(2026, 9, 13).date())
        self.assertEqual(result['apps'], {})
        self.assertEqual(result['recorded'], 0)
        for day in ('2026-02-30', '2026-09-14', 'not-a-date'):
            with self.assertRaises(ValueError):
                self.store.history(day, today=datetime(2026, 9, 13).date())

    def test_history_snapshot_cannot_mutate_storage(self):
        self.store.record('a.exe', self.start, 60)
        result = self.store.history('2026-09-12', today=datetime(2026, 9, 13).date())
        result['apps']['a.exe'] = 999
        result['chart'][5]['apps']['a.exe'] = 999
        self.assertEqual(self.store.usage('2026-09-12'), {'a.exe': 60})

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'daily.json'
        self.store = Store(self.path)
        self.start = datetime(2026, 9, 12, 12).timestamp()

    def tracker(self):
        tracker = Tracker.__new__(Tracker)
        tracker.activity_probe = lambda: (0, True)
        tracker.attendance = namespace['AttendancePolicy']()
        tracker.attendance.max_gap = 30  # Older accounting tests use 10-second fake samples.
        tracker.state_lock = threading.RLock()
        tracker.stop_event = threading.Event()
        tracker.stop_requested = False
        tracker.daily_store = self.store
        tracker.current_app = 'editor.exe'
        tracker.current_window = 'Example document'
        tracker.start_time = self.start
        tracker.started_monotonic = 100
        tracker.session_data = defaultdict(lambda: {'time': 0, 'windows': defaultdict(float)})
        tracker.total_usage = defaultdict(float)
        tracker.save_config = Mock()
        return tracker

    def test_reopen_and_continue_same_day(self):
        self.store.record('editor.exe', self.start, 60)
        reopened = Store(self.path)
        self.assertEqual(reopened.usage('2026-09-12'), {'editor.exe': 60})
        reopened.record('editor.exe', self.start + 600, 40)
        self.assertEqual(Store(self.path).usage('2026-09-12'), {'editor.exe': 100})

    def test_midnight_splits_interval_and_preserves_total(self):
        start = datetime(2026, 9, 12, 23, 59, 50).timestamp()
        self.store.record('browser.exe', start, 25)
        self.assertEqual(self.store.usage('2026-09-12'), {'browser.exe': 10})
        self.assertEqual(self.store.usage('2026-09-13'), {'browser.exe': 15})

    def test_long_interval_crosses_multiple_dates(self):
        self.store.record('editor.exe', self.start, 90000)
        self.assertEqual(sum(row['duration'] for row in self.store.rows()), 90000)
        self.assertEqual(self.store.dates(), ['2026-09-13', '2026-09-12'])

    def test_repeated_history_reads_do_not_write_or_inflate_data(self):
        self.store.record('editor.exe', self.start, 60)
        before = self.path.read_bytes()
        for _ in range(3):
            self.assertEqual(self.store.rows()[0]['duration'], 60)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_replace_does_not_mutate_memory_or_existing_file(self):
        self.store.record('editor.exe', self.start, 60)
        before = self.path.read_bytes()
        with patch.object(os, 'replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.store.record('editor.exe', self.start + 60, 30)
        self.assertEqual(self.store.usage('2026-09-12')['editor.exe'], 60)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob('.daily-*.tmp')), [])

    def test_corrupt_file_is_not_overwritten(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            Store(self.path)
        self.assertEqual(self.path.read_text(encoding='utf-8'), '{broken')

    def test_repeated_stop_records_final_interval_once_including_fraction(self):
        tracker = self.tracker()
        with patch.object(time, 'monotonic', return_value=100.4), \
             patch.object(time, 'time', return_value=self.start + .4):
            tracker.stop_tracking()
            tracker.stop_tracking()
        self.assertAlmostEqual(Store(self.path).usage('2026-09-12')['editor.exe'], .4)
        self.assertIsNone(tracker.current_app)

    def test_clock_discontinuity_is_not_written_as_attended_time(self):
        tracker = self.tracker()
        with patch.object(time, 'monotonic', return_value=110), \
             patch.object(time, 'time', return_value=self.start - 3600):
            tracker.log_app_usage('editor.exe', 'Document')
        self.assertEqual(self.store.usage('2026-09-12'), {})

    def test_selected_history_uses_persisted_data_not_current_session(self):
        self.store.record('editor.exe', self.start, 60)
        app = App.__new__(App)
        app.day_var = SimpleNamespace(get=lambda: '2026-09-12')
        app.tracker = SimpleNamespace(daily_store=Store(self.path), session_data={})
        self.assertEqual(app.overview_usage(), {'editor.exe': 60})

    def test_friendly_date_selection_maps_to_history(self):
        self.store.record('editor.exe', self.start, 60)
        app = App.__new__(App)
        app.day_var = SimpleNamespace(get=lambda: 'Sat, 12 Sep 2026')
        app.day_lookup = {'Sat, 12 Sep 2026': '2026-09-12'}
        app.tracker = SimpleNamespace(daily_store=self.store)
        self.assertEqual(app.overview_usage(), {'editor.exe': 60})

    def test_date_choices_are_not_reconfigured_on_every_timer_tick(self):
        app = App.__new__(App)
        app.day_var = Mock()
        app.day_var.get.return_value = 'Today'
        app.day_lookup = {}
        app.day_choices = None
        app.day_picker = Mock()
        app.tracker = SimpleNamespace(daily_store=self.store)
        app.refresh_day_choices()
        app.refresh_day_choices()
        app.day_picker.configure.assert_called_once()
        app.day_var.set.assert_not_called()

    def test_worker_checkpoints_switch_and_final_interval_once(self):
        tracker = self.tracker()
        tracker.current_app = None
        tracker.start_time = None
        tracker.started_monotonic = None
        tracker.gui = None
        tracker.app_limits = {}
        tracker.warning_times = {}
        tracker.warned_apps = {}
        tracker.get_active_window_info = Mock(side_effect=[('A', 'a.exe'), ('B', 'b.exe')])
        clock = [100]

        def wait(seconds):
            clock[0] += 10
            if clock[0] == 120:
                tracker.stop_requested = True

        with patch.object(tracker.stop_event, 'wait', side_effect=wait), \
             patch.object(time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(time, 'time', side_effect=lambda: self.start + clock[0] - 100):
            tracker.track()
            tracker.stop_tracking()
        self.assertEqual(Store(self.path).usage('2026-09-12'), {'a.exe': 10, 'b.exe': 10})

    def test_limit_uses_restored_today_usage_on_first_sample(self):
        tracker = self.tracker()
        today = datetime.now()
        self.store.record('editor.exe', today.timestamp(), 1)
        tracker.daily_store = Store(self.path)
        tracker.current_app = None
        tracker.start_time = None
        tracker.started_monotonic = None
        tracker.gui = None
        tracker.app_limits = {'editor.exe': .5}
        tracker.warning_times = {}
        tracker.warned_apps = {}
        tracker.get_active_window_info = Mock(return_value=('A', 'editor.exe'))
        tracker.enforce_limit = Mock()

        def wait(seconds):
            tracker.stop_requested = True

        with patch.object(tracker.stop_event, 'wait', side_effect=wait):
            tracker.track()
        tracker.enforce_limit.assert_called_once_with('editor.exe')


if __name__ == '__main__':
    unittest.main()
