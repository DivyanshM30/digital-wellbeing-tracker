"""Opt-in Windows sign-in launch, scoped to the current user."""
from pathlib import Path
import subprocess
import sys


class StartupRegistration:
    key_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
    value_name = 'DigitalWellbeingTracker'

    def __init__(self, script, registry=None, executable=None, frozen=None):
        if registry is None:
            import winreg
            registry = winreg
        self.registry = registry
        self.script = Path(script).resolve()
        self.executable = Path(executable or sys.executable).resolve()
        self.frozen = getattr(sys, 'frozen', False) if frozen is None else frozen

    def command(self):
        executable = self.executable
        if not self.frozen:
            windowed = executable.with_name('pythonw.exe')
            if not windowed.is_file():
                raise OSError('pythonw.exe is missing. Repair your Python environment before enabling startup.')
            executable = windowed
        if not executable.is_file() or (not self.frozen and not self.script.is_file()):
            raise OSError('The application path no longer exists.')
        args = [str(executable)]
        if not self.frozen:
            args.append(str(self.script))
        command = subprocess.list2cmdline([*args, '--startup'])
        if len(command) > 260:
            raise ValueError('Startup command exceeds 260 characters. Move the project to a shorter path.')
        return command

    def enabled(self):
        r = self.registry
        try:
            with r.OpenKey(r.HKEY_CURRENT_USER, self.key_path, 0, r.KEY_READ) as key:
                value, kind = r.QueryValueEx(key, self.value_name)
            return kind == r.REG_SZ and value == self.command()
        except FileNotFoundError:
            return False

    def set_enabled(self, enabled):
        r = self.registry
        if enabled:
            command = self.command()  # Validate before changing the registry.
            with r.CreateKeyEx(r.HKEY_CURRENT_USER, self.key_path, 0, r.KEY_SET_VALUE) as key:
                r.SetValueEx(key, self.value_name, 0, r.REG_SZ, command)
        else:
            try:
                with r.OpenKey(r.HKEY_CURRENT_USER, self.key_path, 0, r.KEY_SET_VALUE) as key:
                    r.DeleteValue(key, self.value_name)
            except FileNotFoundError:
                pass
