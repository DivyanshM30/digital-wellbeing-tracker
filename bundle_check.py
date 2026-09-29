"""Opt-in bundled-runtime check; only temporary synthetic data is used."""
import json
from pathlib import Path
import sys
import tempfile
import traceback
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch


def run_check(module, output):
    report = {'ok': False, 'frozen': bool(getattr(sys, 'frozen', False))}
    root = None
    try:
        with tempfile.TemporaryDirectory() as folder:
            store = module.DailyUsageStore(Path(folder) / 'history.json')
            store.record('demo.exe', datetime(2026, 1, 1, 12).timestamp(), 120)
            assert module.DailyUsageStore(store.path).days == store.days
            tracker = SimpleNamespace(session_data={}, current_app=None,
                current_window=None, start_time=None, app_limits={},
                warning_times={}, save_config=Mock(), daily_store=store)
            with patch.object(module, 'ScreenTimeTracker', return_value=tracker), \
                 patch.object(module.DigitalWellnessApp, 'load_app_settings'), \
                 patch.object(module.DigitalWellnessApp, 'save_app_settings'), \
                 patch.object(module.DigitalWellnessApp, 'setup_system_tray'), \
                 patch.object(module.DigitalWellnessApp, 'schedule_auto_analysis'):
                root = module.tk.Tk()
                root.withdraw()
                app = module.DigitalWellnessApp(root)
                app.notebook.select(app.history_frame)
                app.history_date.set('2026-01-01')
                app.refresh_history()
                assert len(app.history_tree.get_children()) == 1
                for dark in (False, True):
                    app.dark_mode.set(dark)
                    app.toggle_theme()
                    root.update()
                    app.history_canvas.draw()
                root.destroy()
                root = None
            module.KMeans(n_clusters=2, n_init=1, random_state=0).fit(
                [[0., 0.], [1., 1.], [10., 10.], [11., 11.]])
            import importlib
            importlib.import_module('plyer.platforms.win.notification')
            importlib.import_module('pystray._win32')
            importlib.import_module('pyttsx3.drivers.sapi5')
            report.update(ok=True, checks=['atomic storage reload', 'Tk History',
                'light and dark themes', 'matplotlib canvas', 'KMeans',
                'Windows notification, tray and speech imports'])
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if root is not None:
            root.destroy()
        Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1
