"""Thread handoffs tested without Tk, audio hardware, or personal usage data."""
import queue
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_daily_usage as daily


class BackgroundTests(unittest.TestCase):
    def app(self):
        app = daily.App.__new__(daily.App)
        app.closing = False
        app.analysis_running = False
        app.ui_actions = queue.Queue()
        app.tracker = Mock()
        return app

    def test_analysis_returns_while_snapshot_is_blocked_and_coalesces_clicks(self):
        app = self.app()
        entered, release = threading.Event(), threading.Event()
        calls = []
        def rows():
            calls.append(threading.get_ident())
            entered.set()
            release.wait(3)
            return []
        app.tracker.daily_store.rows.side_effect = rows
        pd = Mock()
        pd.DataFrame.return_value.empty = True
        dialogs = Mock()
        with patch.dict(daily.namespace, pd=pd, messagebox=dialogs):
            try:
                app.analyze_usage()
                self.assertTrue(entered.wait(2))
                app.analyze_usage()
                self.assertTrue(app.analysis_running)
                self.assertEqual(len(calls), 1)
                self.assertNotEqual(calls[0], threading.get_ident())
                dialogs.showinfo.assert_not_called()
            finally:
                release.set()
            completion = app.ui_actions.get(timeout=3)
            dialogs.showinfo.assert_not_called()
            completion()
            self.assertFalse(app.analysis_running)
            dialogs.showinfo.assert_called_once_with('Smart Insights', 'No usage data available.')

    def test_analysis_failure_is_delivered_on_ui_queue_and_can_retry(self):
        app = self.app()
        app.tracker.daily_store.rows.side_effect = ValueError('broken snapshot')
        dialogs = Mock()
        with patch.dict(daily.namespace, pd=Mock(), messagebox=dialogs), \
                patch('builtins.open', side_effect=OSError('read only')):
            app.analyze_usage()
            callback = app.ui_actions.get(timeout=3)
            dialogs.showerror.assert_not_called()
            callback()
            self.assertFalse(app.analysis_running)
            dialogs.showerror.assert_called_once_with('Smart Insights', 'Failed to analyze usage: broken snapshot')
            app.analyze_usage()
            app.ui_actions.get(timeout=3)()
            self.assertEqual(dialogs.showerror.call_count, 2)

    def test_late_completion_does_not_touch_destroyed_widgets(self):
        app = self.app()
        app.closing = True
        app._analysis_complete(recommendation='late', today_str='2026-09-21')
        app.tracker.voice_alert.assert_not_called()

    def test_success_renders_and_marks_day_only_on_completion(self):
        app = self.app()
        app.analysis_running = True
        app.recommendation_text = Mock()
        with patch.dict(daily.namespace, tk=SimpleNamespace(NORMAL='normal', END='end', DISABLED='disabled')):
            app._analysis_complete('2026-09-21', 'Today: Low Usage', 'Check your insights.')
        app.recommendation_text.insert.assert_called_once_with('end', 'Today: Low Usage')
        app.tracker.voice_alert.assert_called_once_with('Check your insights.')
        self.assertEqual(app.insights_generated_for, '2026-09-21')
        self.assertFalse(app.analysis_running)

    def test_voice_setting_is_read_only_when_ui_drains_queue(self):
        tracker = daily.Tracker.__new__(daily.Tracker)
        tracker.gui = self.app()
        tracker.gui.voice_alerts_var = Mock()
        tracker.speech = Mock()
        tracker.voice_alert('hello')
        tracker.gui.voice_alerts_var.get.assert_not_called()
        tracker.gui.voice_alerts_var.get.return_value = False
        tracker.gui.ui_actions.get_nowait()()
        tracker.speech.say.assert_not_called()
        tracker.gui.voice_alerts_var.get.return_value = True
        tracker.voice_alert('enabled')
        tracker.gui.ui_actions.get_nowait()()
        tracker.speech.say.assert_called_once_with('enabled')

    def test_speech_owns_com_and_engine_on_one_worker_and_close_never_waits(self):
        events = []
        speaking, release = threading.Event(), threading.Event()
        def record(name):
            events.append((name, threading.get_ident()))
        engine = Mock()
        engine.stop.side_effect = lambda: record('stop')
        engine.say.side_effect = lambda message: record(message)
        def run():
            record('run')
            speaking.set()
            release.wait(3)
        engine.runAndWait.side_effect = run
        def initialize():
            record('init')
            return engine
        com = SimpleNamespace(CoInitialize=lambda: record('com-init'),
                              CoUninitialize=lambda: record('com-done'))
        with patch.dict(sys.modules, pythoncom=com), \
                patch.dict(daily.namespace, pyttsx3=SimpleNamespace(init=initialize)):
            worker = daily.namespace['SpeechWorker']()
            try:
                worker.say('first')
                self.assertTrue(speaking.wait(2))
                worker.say('discard on exit')
                worker.close()
                self.assertTrue(worker.thread.is_alive())
            finally:
                release.set()
                worker.close()
                worker.thread.join(3)
            self.assertFalse(worker.thread.is_alive())
        self.assertEqual(len({ident for _, ident in events}), 1)
        self.assertNotEqual(events[0][1], threading.get_ident())
        self.assertEqual(events[0][0], 'com-init')
        self.assertEqual(events[-1][0], 'com-done')
        self.assertNotIn('discard on exit', [name for name, _ in events])
