"""Exercise Overview behavior without starting Windows monitoring or a GUI.

Load the actual application class via AST so these focused tests also run when
the optional desktop dependencies are unavailable. They do not verify layout.
"""
import ast
from collections import defaultdict
from pathlib import Path
import queue
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


source = ast.parse((Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8"))
app_class = next(node for node in source.body
                 if isinstance(node, ast.ClassDef) and node.name == "DigitalWellnessApp")
namespace = {"time": time, "queue": queue}
exec(compile(ast.Module(body=[app_class], type_ignores=[]), "main.py", "exec"), namespace)
App = namespace["DigitalWellnessApp"]


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.tracking_active = True
        self.app.tracker = SimpleNamespace(
            session_data=defaultdict(lambda: {"time": 0}), current_app=None,
            current_window=None, start_time=None, app_limits={}, warning_times={})

    def test_first_active_app_appears_before_any_switch_without_mutating_storage(self):
        self.app.tracker.current_app = "editor.exe"
        self.app.tracker.start_time = 100
        with patch.object(time, "time", return_value=125):
            self.assertEqual(self.app.overview_usage(), {"editor.exe": 25})
        self.assertEqual(dict(self.app.tracker.session_data), {})

    def test_pause_does_not_add_elapsed_time_and_negative_clock_delta_is_clamped(self):
        self.app.tracker.session_data["editor.exe"] = {"time": 40}
        self.app.tracker.current_app = "editor.exe"
        self.app.tracker.start_time = 100
        self.app.tracking_active = False
        with patch.object(time, "time", return_value=200):
            self.assertEqual(self.app.overview_usage(), {"editor.exe": 40})
        self.app.tracking_active = True
        with patch.object(time, "time", return_value=90):
            self.assertEqual(self.app.overview_usage(), {"editor.exe": 40})

    def test_usage_is_sorted_with_stable_ties_and_excludes_zero_history(self):
        self.app.tracker.session_data.update({
            "z.exe": {"time": 60}, "a.exe": {"time": 60},
            "b.exe": {"time": 100}, "old.exe": {"time": 0}})
        self.assertEqual(list(self.app.overview_usage()), ["b.exe", "a.exe", "z.exe"])

    def prepare_rows(self):
        self.app.summary_values = [Mock() for _ in range(3)]
        self.app.summary_details = [Mock() for _ in range(3)]
        self.app.empty_usage = Mock()
        self.app.paint_usage_bar = Mock()
        self.app.overview_rows = [dict(frame=Mock(), name=Mock(), duration=Mock(),
                                       detail=Mock()) for _ in range(5)]

    def test_totals_include_apps_outside_top_five_and_widgets_are_reused(self):
        self.prepare_rows()
        rows = list(self.app.overview_rows)
        usage = {f"app{i}.exe": 60 for i in range(6)}
        self.app.update_progress_bars(usage)
        self.app.summary_values[0].config.assert_called_with(text="00:06:00")
        self.assertAlmostEqual(rows[0]["fraction"], 1 / 6)
        self.app.update_progress_bars(usage)
        self.assertEqual(self.app.overview_rows, rows)
        for row in rows:
            row["frame"].destroy.assert_not_called()

    def test_threshold_status_and_progress_are_distinct_from_unlimited_share(self):
        self.prepare_rows()
        self.app.tracker.app_limits = {"over.exe": 100, "near.exe": 100}
        self.app.tracker.warning_times = {"near.exe": 70}
        self.app.update_progress_bars({"over.exe": 125, "near.exe": 75, "free.exe": 50})
        self.app.summary_values[2].config.assert_called_with(text="2 apps")
        over, near, free = self.app.overview_rows[:3]
        self.assertEqual((over["fraction"], over["color"]), (1, "danger"))
        self.assertEqual((near["fraction"], near["color"]), (.75, "warning"))
        self.assertEqual((free["fraction"], free["color"]), (.2, "accent"))

    def test_empty_state_hides_rows_and_clears_summaries(self):
        self.prepare_rows()
        self.app.update_progress_bars({})
        self.app.summary_values[0].config.assert_called_with(text="00:00:00")
        self.app.summary_values[1].config.assert_called_with(text="—")
        for row in self.app.overview_rows:
            row["frame"].pack_forget.assert_called_once()

    def test_ui_timer_runs_queued_tray_actions_and_uses_one_snapshot(self):
        self.app.ui_actions = queue.Queue()
        action = Mock()
        self.app.ui_actions.put(action)
        self.app.closing = False
        self.app.root = Mock()
        self.app.last_chart_refresh = 0
        self.app.tracking_badge = Mock()
        self.app.current_app_label = Mock()
        self.app.current_window_label = Mock()
        self.app.update_progress_bars = Mock()
        self.app.update_stats_display = Mock()
        with patch.object(time, "monotonic", return_value=10):
            self.app.update_ui()
        action.assert_called_once()
        self.app.root.after.assert_called_once_with(1000, self.app.update_ui)
        self.app.update_progress_bars.assert_called_once_with({})
        self.app.update_stats_display.assert_called_once_with({})


if __name__ == "__main__":
    unittest.main()
