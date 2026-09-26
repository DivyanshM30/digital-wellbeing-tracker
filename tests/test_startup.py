"""Startup tests use a fake registry; they never enable startup on the host."""
from pathlib import Path
import ast
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, Mock, patch

from startup import StartupRegistration
import test_daily_usage as daily


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='tracker startup ')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name).resolve()
        self.script = self.folder / 'main.py'
        self.python = self.folder / 'python.exe'
        self.windowed = self.folder / 'pythonw.exe'
        for file in (self.script, self.python, self.windowed):
            file.touch()
        self.registry = MagicMock()
        self.registry.REG_SZ = 1
        self.values = {'OtherApplication': 'keep me'}
        def query(key, name):
            if name not in self.values:
                raise FileNotFoundError(name)
            return self.values[name], 1
        def delete(key, name):
            if name not in self.values:
                raise FileNotFoundError(name)
            del self.values[name]
        self.registry.QueryValueEx.side_effect = query
        self.registry.SetValueEx.side_effect = lambda key, name, reserved, kind, value: self.values.update({name: value})
        self.registry.DeleteValue.side_effect = delete
        self.registration = StartupRegistration(self.script, self.registry, self.python, False)

    def test_enable_disable_roundtrip_only_changes_our_current_user_value(self):
        self.assertFalse(self.registration.enabled())
        self.registration.set_enabled(True)
        self.assertTrue(self.registration.enabled())
        self.registry.CreateKeyEx.assert_called_once_with(self.registry.HKEY_CURRENT_USER,
            self.registration.key_path, 0, self.registry.KEY_SET_VALUE)
        self.registration.set_enabled(False)
        self.registration.set_enabled(False)
        self.assertFalse(self.registration.enabled())
        self.assertEqual(self.values, {'OtherApplication': 'keep me'})

    def test_source_command_quotes_paths_and_uses_windowed_python(self):
        self.assertEqual(self.registration.command(), subprocess.list2cmdline(
            [str(self.windowed), str(self.script), '--startup']))
        self.assertIn('"', self.registration.command())

    def test_packaged_command_launches_executable_without_script(self):
        registration = StartupRegistration(self.script, self.registry, self.python, True)
        self.assertEqual(registration.command(), subprocess.list2cmdline([str(self.python), '--startup']))

    def test_missing_pythonw_does_not_write_entry(self):
        self.windowed.unlink()
        with self.assertRaises(OSError):
            self.registration.set_enabled(True)
        self.registry.SetValueEx.assert_not_called()

    def test_oversized_command_does_not_write_entry(self):
        self.registration.script = self.folder / ('x' * 240 + '.py')
        with patch.object(Path, 'is_file', return_value=True), self.assertRaises(ValueError):
            self.registration.set_enabled(True)
        self.registry.SetValueEx.assert_not_called()

    def test_stale_path_is_not_reported_as_enabled(self):
        self.values[self.registration.value_name] = 'old path --startup'
        self.assertFalse(self.registration.enabled())


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.app = daily.App.__new__(daily.App)
        self.app.root = Mock()
        self.app.status_bar = Mock()
        self.app.start_tracking = Mock()
        self.app.tray_ready = threading.Event()
        self.app.closing = False

    def test_manual_launch_shows_window_without_auto_tracking(self):
        self.app.apply_launch_mode(False)
        self.app.root.deiconify.assert_called_once()
        self.app.start_tracking.assert_not_called()

    def test_startup_tracks_and_keeps_window_hidden_when_tray_ready(self):
        self.app.tray_ready.set()
        self.app.apply_launch_mode(True)
        self.app.check_startup_tray()
        self.app.start_tracking.assert_called_once()
        self.app.root.after.assert_called_once_with(5000, self.app.check_startup_tray)
        self.app.root.deiconify.assert_not_called()

    def test_missing_tray_shows_window_but_shutdown_does_not(self):
        self.app.check_startup_tray()
        self.app.root.deiconify.assert_called_once()
        self.app.root.reset_mock()
        self.app.closing = True
        self.app.check_startup_tray()
        self.app.root.deiconify.assert_not_called()

    def test_registration_failure_reverts_checkbox_and_reports_error(self):
        self.app.start_with_windows_var = Mock()
        self.app.start_with_windows_var.get.return_value = True
        self.app.startup_registration = Mock()
        self.app.startup_registration.set_enabled.side_effect = PermissionError('denied')
        dialogs = Mock()
        with patch.dict(daily.namespace, messagebox=dialogs):
            self.app.toggle_windows_startup()
        self.app.start_with_windows_var.set.assert_called_once_with(False)
        dialogs.showerror.assert_called_once()


class EntryPointTests(unittest.TestCase):
    def run_main(self, duplicate=False):
        with tempfile.TemporaryDirectory() as folder:
            namespace = dict(daily.namespace)
            namespace['__file__'] = str(Path(folder) / 'main.py')
            namespace['tk'] = Mock()
            namespace['messagebox'] = Mock()
            namespace['DigitalWellnessApp'] = Mock()
            function = next(node for node in daily.tree.body
                            if isinstance(node, ast.FunctionDef) and node.name == 'main')
            exec(compile(ast.Module(body=[function], type_ignores=[]), 'main.py', 'exec'), namespace)
            lock = Mock()
            if duplicate:
                lock.locking.side_effect = OSError('already running')
            with patch.dict('sys.modules', msvcrt=lock), \
                 patch.object(daily.sys, 'argv', ['main.py', '--startup']), \
                 patch.object(daily.os, 'chdir') as chdir:
                namespace['main']()
                chdir.assert_called_once_with(Path(folder).resolve())
            return namespace

    def test_sign_in_reuses_application_directory_and_passes_launch_mode(self):
        namespace = self.run_main()
        namespace['DigitalWellnessApp'].return_value.apply_launch_mode.assert_called_once_with(True)
        namespace['tk'].Tk.return_value.mainloop.assert_called_once()

    def test_duplicate_sign_in_launch_exits_quietly(self):
        namespace = self.run_main(duplicate=True)
        namespace['DigitalWellnessApp'].assert_not_called()
        namespace['messagebox'].showinfo.assert_not_called()
        namespace['tk'].Tk.return_value.destroy.assert_called_once()
