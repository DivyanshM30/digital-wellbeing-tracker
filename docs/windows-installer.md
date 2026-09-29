# Windows installer

The desktop build bundles Python, Tk, themes, charts, and tracking dependencies.
The installer runs for the current user without administrator access. It creates
a Start menu shortcut and offers an optional desktop shortcut. Windows startup
remains opt-in in the app's Settings.

## Build on Windows x64

Use 64-bit Python 3.12 with Tcl/Tk and [Inno Setup 6](https://jrsoftware.org/isdl.php)
(the local build was compiled with 6.7.3). From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r packaging/requirements-build.txt
.\scripts\build-windows.ps1
```

Python dependencies are constrained to the locally validated versions in
`packaging/constraints-windows.txt`; review and refresh that file when upgrading
dependencies. Build a release in a fresh virtual environment to avoid collecting
unrelated optional packages from a development environment.

If the compiler is elsewhere, pass `-Iscc 'C:\path\to\ISCC.exe'`. Use
`-BundleOnly` to check the executable without compiling the installer. The script
runs regression tests, builds a windowed PyInstaller folder bundle, launches its
isolated `--self-test`, and then compiles Setup. The self-test uses temporary
synthetic history and mocks tracking, settings, tray creation, and scheduling;
it does not monitor applications, speak, or modify startup registration.

Outputs (ignored by Git):

- `dist/installer/DigitalWellbeingTracker-0.1.0-Setup-x64.exe`
- The adjacent `.exe.sha256` checksum
- `dist/bundle-check.json`, the bundled-runtime check report

Change `packaging/desktop-version.txt` before a release. The stable installer
AppId must remain unchanged for upgrades. Never distribute the bundle's `.exe`
alone: its `_internal` directory is required. Distribute the Setup executable.
The optional **Windows installer** GitHub Actions workflow builds downloadable
artifacts when manually run; it does not publish a release.

## Data and upgrades

Programs install under `%LOCALAPPDATA%\Programs\DigitalWellbeingTracker`.
The installed app saves its history, settings, limits, and lock under
`%LOCALAPPDATA%\DigitalWellbeingTracker`. This is independent of the program
folder, so installing an update does not replace personal data. Running
`python main.py` continues to use data beside `main.py`.

Before updating or uninstalling, choose **Exit** from the tray menu (closing the
window only hides it). Uninstall leaves history and preferences in Local AppData
and removes the startup entry only when it points to that installed executable.
Delete the data folder yourself after backing it up if you want to erase history.

### Move existing source history

Migration is manual: the installer cannot reliably identify which old checkout
contains your authoritative history. Exit both versions first. Back up the source
`data` folder, `config.json`, `app_settings.json`, and optional legacy `logs`.
Copy these into `%LOCALAPPDATA%\DigitalWellbeingTracker` before first launch;
omit `data/tracker.lock`. Do not replace existing destination history without a
backup, and do not concatenate JSON files. The app's existing atomic history
format and legacy recovery remain unchanged. Enable **Start with Windows** in
the installed app afterward to replace any old source startup command.

## Verify before distribution

1. Exit the source tracker. Run Setup and open the Start menu shortcut. Check
   Overview, History, light/dark themes, tray Show/Exit, and Insights.
2. Start tracking, use an app for a minute, then stop and exit from the tray.
   Reopen and confirm today's saved total. Check the Local AppData data folder.
3. Check idle, lock, and sleep/resume behavior; unattended time should be excluded.
4. Enable startup, sign out/in, and check tray tracking. Verify speech and alerts
   on your actual Windows voice/audio configuration.
5. Exit, reinstall the same Setup, and confirm history and preferences survive.
   Uninstall, confirm data remains, then reinstall and verify it is restored.
6. Repeat installation on a clean Windows x64 machine without Python installed.

The local bundle check is not a clean-machine or real sign-in test. The installer
is unsigned; Windows may display an unknown-publisher/SmartScreen prompt. Review
the publisher and source before running. Code signing and a published GitHub
release remain separate release tasks. No installer download link is advertised
on the landing page until an actual release is published.
