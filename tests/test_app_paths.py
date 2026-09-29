import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
from app_paths import application_home


class ApplicationHomeTests(unittest.TestCase):
    def test_source_keeps_existing_repository_data(self):
        script = Path(__file__).resolve().parents[1] / 'main.py'
        self.assertEqual(application_home(script, frozen=False), script.parent)

    def test_bundle_data_is_independent_of_program_location(self):
        with tempfile.TemporaryDirectory() as folder:
            environment = {'LOCALAPPDATA': folder}
            expected = Path(folder) / 'DigitalWellbeingTracker'
            for script in ('old/_internal/main.py', 'new/_internal/main.py'):
                self.assertEqual(application_home(script, frozen=True,
                    environment=environment), expected)
            self.assertFalse(expected.exists())

    def test_missing_profile_fails_without_falling_back_to_bundle(self):
        with self.assertRaises(OSError):
            application_home('main.py', frozen=True, environment={})

    def test_bundled_store_reopens_history_after_program_moves(self):
        from test_daily_usage import namespace
        from datetime import datetime
        import os
        store_type = namespace['DailyUsageStore']
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(sys, 'frozen', True, create=True), \
             patch.dict(os.environ, LOCALAPPDATA=folder):
            with patch.dict(namespace, __file__=str(Path(folder) / 'old/main.py')):
                store = store_type()
                store.record('demo.exe', datetime(2026, 1, 1, 12).timestamp(), 60)
            with patch.dict(namespace, __file__=str(Path(folder) / 'new/main.py')):
                reopened = store_type()
                self.assertEqual(store.path, reopened.path)
                self.assertEqual(store.days, reopened.days)
                self.assertEqual(store.hours, reopened.hours)
            self.assertFalse((Path(folder) / 'old').exists())
            self.assertFalse((Path(folder) / 'new').exists())
