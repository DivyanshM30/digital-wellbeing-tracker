"""Windows UI smoke check: run from the repository root with the app closed.

Uses the normal app and saved settings/data. Analysis waits ten extra seconds;
the speech probe runs once after startup if Voice reminders is enabled.
No synthetic usage is written. Close using tray > Exit as usual.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main

original_analysis = main.DigitalWellnessApp._analyze_usage_worker
original_init = main.DigitalWellnessApp.__init__


def delayed_analysis(self):
    time.sleep(10)
    original_analysis(self)


def with_speech_probe(self, root):
    original_init(self, root)
    root.after(3000, lambda: self.tracker.voice_alert(
        'Responsiveness check. While this reminder is speaking, resize the window, '
        'switch between Overview, History, and Settings, and change the theme. '
        'The application should continue responding throughout this reminder. ' * 3))


if __name__ == '__main__':
    main.DigitalWellnessApp._analyze_usage_worker = delayed_analysis
    main.DigitalWellnessApp.__init__ = with_speech_probe
    main.main()
