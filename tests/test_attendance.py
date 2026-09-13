"""Deterministic transition tests; no real locking, sleeping, or input injection."""
from datetime import datetime
import ctypes
from ctypes import wintypes
from unittest.mock import Mock, patch
import time
import unittest

import test_daily_usage as daily

namespace = daily.namespace
Store = daily.Store

Policy = namespace['AttendancePolicy']


class WindowsActivityTests(unittest.TestCase):
    def setUp(self):
        self.user = Mock()
        self.kernel = Mock()
        self.session = Mock(WTS_CURRENT_SESSION=-1, WTSConnectState=8, WTSActive=0)
        self.session.WTSQuerySessionInformation.return_value = 0
        self.kernel.GetTickCount64.return_value = (1 << 32) + 500
        def input_info(pointer):
            pointer._obj.dwTime = (1 << 32) - 500
            return True
        self.user.GetLastInputInfo.side_effect = input_info
        self.user.OpenInputDesktop.return_value = 42
        self.desktop_name = 'Default'
        def desktop_info(handle, field, name, size, needed):
            name.value = self.desktop_name
            return True
        self.user.GetUserObjectInformationW.side_effect = desktop_info
        self.addCleanup(patch.stopall)
        patch.dict(namespace, ctypes=ctypes, wintypes=wintypes, win32ts=self.session).start()
        patch.object(ctypes, 'WinDLL', create=True, side_effect=[self.user, self.kernel]).start()
        self.probe = namespace['WindowsActivity']()

    def test_input_tick_wrap_and_default_desktop(self):
        self.assertEqual(self.probe(), (1, True))
        self.user.CloseDesktop.assert_called_once_with(42)

    def test_secure_desktop_is_unavailable_and_handle_is_closed(self):
        self.desktop_name = 'Winlogon'
        self.assertEqual(self.probe(), (1, False))
        self.user.CloseDesktop.assert_called_once_with(42)

    def test_disconnected_session_is_unavailable_even_with_default_desktop(self):
        self.session.WTSQuerySessionInformation.return_value = 4
        self.assertEqual(self.probe(), (1, False))
        self.user.OpenInputDesktop.assert_not_called()

    def test_failed_session_query_pauses_conservatively(self):
        self.session.WTSQuerySessionInformation.side_effect = OSError('unavailable')
        self.assertEqual(self.probe(), (1, False))

    def test_failed_input_query_pauses(self):
        self.user.GetLastInputInfo.side_effect = None
        self.user.GetLastInputInfo.return_value = False
        self.assertEqual(self.probe(), (0, False))

    def test_inaccessible_desktop_pauses(self):
        self.user.OpenInputDesktop.return_value = None
        self.assertEqual(self.probe(), (1, False))
        self.user.CloseDesktop.assert_not_called()


class AttendancePolicyTests(unittest.TestCase):
    def test_idle_boundary_counts_only_attended_prefix(self):
        policy = Policy()
        self.assertEqual(policy.duration(1, 1, 59, True), 1)
        self.assertEqual(policy.duration(1, 1, 60, True), 1)
        self.assertAlmostEqual(policy.duration(1, 1, 60.4, True), .6)
        self.assertEqual(policy.duration(1, 1, 61, True), 0)

    def test_locked_unknown_or_suspend_intervals_are_excluded(self):
        policy = Policy()
        for elapsed, wall, idle, available in ((1, 1, 0, False), (600, 600, 0, True),
                (1, 600, 0, True), (1, -600, 0, True), (1, 1, float('nan'), True)):
            with self.subTest(elapsed=elapsed, wall=wall, available=available):
                self.assertEqual(policy.duration(elapsed, wall, idle, available), 0)


class AttendanceTransitions(unittest.TestCase):
    def setUp(self):
        self.fixture = daily.DailyUsageTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.tracker = self.fixture.tracker()
        self.tracker.attendance = Policy()

    def run_samples(self, samples, gaps):
        tracker = self.tracker
        tracker.current_app = tracker.current_window = tracker.start_time = tracker.started_monotonic = None
        tracker.gui = None
        tracker.app_limits = {}
        tracker.warning_times = {}
        tracker.warned_apps = {}
        tracker.get_active_window_info = Mock(return_value=('Document', 'editor.exe'))
        state = [0, 100.0]
        tracker.activity_probe = lambda: samples[state[0]]

        def wait(seconds):
            if state[0] == len(samples) - 1:
                tracker.stop_requested = True
            else:
                state[1] += gaps[state[0]]
                state[0] += 1

        with patch.object(time, 'monotonic', side_effect=lambda: state[1]), \
             patch.object(time, 'time', side_effect=lambda: self.fixture.start + state[1] - 100), \
             patch.object(tracker.stop_event, 'wait', side_effect=wait):
            tracker.track()
            tracker.stop_tracking()
        return sum(row['duration'] for row in Store(self.fixture.path).rows()) if self.fixture.path.exists() else 0

    def test_idle_then_input_resumes_without_backfilling_idle(self):
        # 1 active second + 1 up to cutoff + 1 after resume.
        total = self.run_samples([(58, True), (59, True), (60.5, True),
                                  (70, True), (0, True), (1, True)], [1, 1.5, 1, 1, 1])
        self.assertAlmostEqual(total, 3)  # The 1.5-second interval contains 1 second before cutoff.

    def test_lock_discards_boundary_and_unlock_starts_fresh(self):
        total = self.run_samples([(0, True), (1, True), (0, False),
                                  (0, False), (0, True), (1, True)], [1, 1, 1, 1, 1])
        self.assertEqual(total, 2)

    def test_resume_after_long_gap_does_not_charge_sleep_to_active_app(self):
        total = self.run_samples([(0, True), (1, True), (0, True), (1, True)], [1, 3600, 1])
        self.assertEqual(total, 2)

    def test_start_while_idle_never_records_until_input(self):
        self.assertEqual(self.run_samples([(100, True), (101, True), (0, True), (1, True)], [1, 1, 1]), 1)

    def test_stop_while_locked_does_not_commit_pending_interval(self):
        tracker = self.tracker
        tracker.activity_probe = lambda: (0, False)
        with patch.object(time, 'monotonic', return_value=101), \
             patch.object(time, 'time', return_value=self.fixture.start + 1):
            tracker.stop_tracking()
            tracker.stop_tracking()
        self.assertFalse(self.fixture.path.exists())

    def test_idle_transition_across_midnight_keeps_atomic_day_split(self):
        tracker = self.tracker
        tracker.start_time = datetime(2026, 9, 12, 23, 59, 59).timestamp()
        tracker.activity_probe = lambda: (60.5, True)
        with patch.object(time, 'monotonic', return_value=102), \
             patch.object(time, 'time', return_value=tracker.start_time + 2):
            tracker.stop_tracking()
        reopened = Store(self.fixture.path)
        self.assertEqual(reopened.usage('2026-09-12')['editor.exe'], 1)
        self.assertEqual(reopened.usage('2026-09-13')['editor.exe'], .5)
