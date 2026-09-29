"""Keep installed application data independent of upgradeable program files."""
import os
from pathlib import Path
import sys


def application_home(script, *, frozen=None, environment=None):
    frozen = getattr(sys, 'frozen', False) if frozen is None else frozen
    if not frozen:
        return Path(script).resolve().parent
    environment = os.environ if environment is None else environment
    local = environment.get('LOCALAPPDATA')
    if not local:
        raise OSError('Windows Local AppData is unavailable; cannot locate saved usage.')
    return Path(local) / 'DigitalWellbeingTracker'
