# Digital Wellbeing Tracker

A Windows desktop app that tracks time spent in foreground applications, displays usage charts, and provides configurable limits and reminders. Built with Python and Tkinter, with a separate static landing page.

This README describes **main.py**, the entry point currently tracked in Git. The local workspace also contains untracked experimental versions (main2.py, main3.py, and main4.py) with different features and configuration formats.

## Verified source version

GitHub HEAD was checked during this review: commit `73234d37e788983555d313a3adba4131bb75f6e2`. Its `main.py` matches local `main.py` exactly under Git's content hashing (blob `e04adb053e327d897031b930095c78273d97557a`). Local `main3.py` has different content; it is not the current GitHub entry point. The local branch is one commit ahead and one behind the remote, but their `main.py` content matches.

## Features

- Foreground process and window-title monitoring, sampled roughly once per second.
- Dashboard with current application usage, limit progress, and a usage chart.
- Per-application limits and warning thresholds, entered in seconds.
- Voice alerts, desktop notifications, and optional application termination.
- Light/dark themes and system-tray controls.
- Local JSON settings, text session logs, and CSV history.
- Smart Insights using pandas and scikit-learn K-means clustering, requiring at least three dates of usage. These are statistical summaries, not an external AI service.

**Current limitations:** foreground time includes idle time. Dashboard totals and limits use in-memory session data rather than reliable calendar-day totals. Repeated analysis can duplicate historical totals. See [the improvement review](IMPROVEMENTS.md).

## Requirements

- Windows with an interactive desktop. This entry point imports Windows APIs directly; macOS and Linux are not supported.
- Python 3 with pip and Tcl/Tk support. A supported Python version range has not yet been declared or tested.
- Git for cloning; Windows speech voices for voice alerts.

Dependencies include psutil, pywin32, pyttsx3, matplotlib, pystray, Pillow, plyer, sv_ttk, pandas, and scikit-learn. The requirements file also lists `tk`; actual tkinter support must come from your Python installation.

## Setup and launch

Run in PowerShell:

```powershell
git clone https://github.com/DivyanshM30/digital-wellbeing-tracker.git
cd digital-wellbeing-tracker
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m tkinter
.\.venv\Scripts\python.exe main.py
```

The Tkinter command opens a test window; close it before launching the tracker. Calling the environment's Python directly avoids needing PowerShell activation.

Run from the project directory: data paths resolve relative to the working directory. No API key or external database is required.

## Usage

1. Open **Settings** and choose alert preferences. **Auto Shutdown Apps at Limit defaults to enabled** on a fresh setup. Disable it for reminders without termination; closing a process can lose unsaved work. This option closes applications, not Windows.
2. Select **Start Tracking**.
3. In **App Limits**, use **Detect Apps** or enter a lowercase process name such as `chrome.exe`. Values are seconds: for example, a 3,600-second limit and a warning at 2,880 seconds of accumulated use.
4. Switch applications and view the dashboard. Select **Stop Tracking** to pause collection.
5. Use **Smart Insights → Analyze My Usage** after collecting at least three dates of history. Currently this action also writes CSV data, and repeated clicks can duplicate totals.
6. Closing the window hides it when minimizing to the tray is enabled; tracking can continue. Use the tray's exit action to quit.

## Data and privacy

The desktop implementation stores data locally in plain-text files:

| Path | Purpose |
| --- | --- |
| `config.json` | Limits, warning thresholds, and cumulative usage |
| `app_settings.json` | UI and alert preferences; saved when the theme is applied |
| `logs/YYYY-MM-DD.log` | Process names, window titles, timestamps, and durations |
| `usage_log.csv` | `date,app,duration` records, with duration in seconds |
| `error_log.txt` | Analysis errors |

Window titles can contain document names or browser page titles. Treat logs as personal data and exclude them from source control. There is no retention or deletion UI. Exit the app before backing up or manually removing generated data.

The separate landing page uses local assets and system fonts, with no external font or icon scripts.

## Project layout

```text
main.py                    Desktop UI and tracking logic
requirements.txt           Python dependencies, currently unpinned
index.html                 Static landing page
landing_page/
  styles.css               Page styling
  script.js                Copy-to-clipboard setup interaction
  pic/                     Landing-page images
  downloads/               Source archive and download assets
readme.md                  Setup and usage
IMPROVEMENTS.md            Prioritized review and suggested work
```

Local prototypes, generated data, and Windows shortcuts may also appear. A `.lnk` is a shortcut, not an executable. The landing page now provides source installation instructions instead of linking to a shortcut; a verified installer is still needed.

## Preview the landing page

From the project root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8000 --bind 127.0.0.1
```

Open [the local page](http://127.0.0.1:8000). Press Ctrl+C to stop. No Node.js build step is required. The responsive page includes a project screenshot, setup commands, and expandable answers about data, limitations, and Windows support.

## Build a Windows executable

An initial local build command is:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --onefile --collect-data sv_ttk --name DigitalWellbeingTracker main.py
```

Expected output: `dist/DigitalWellbeingTracker.exe`. This recipe was not validated during the review. Test launch, themes, charts, speech, tray actions, and data saving on a clean Windows machine before publishing. Data is still written relative to the working directory.

## Troubleshooting

- **Python unavailable:** install Python with pip and Tcl/Tk, then reopen PowerShell.
- **win32gui missing:** install dependencies using the same virtual-environment Python used to launch.
- **Tkinter test fails:** repair Python's Tcl/Tk installation; a pip package alone does not provide it.
- **No voice output:** check installed Windows voices and the Voice Alerts setting.
- **No insights:** at least three distinct dates must exist in the usage CSV; current history-writing limitations affect results.
- **Window disappears:** check the Windows notification area for the tray icon.
- **Different settings or totals:** launch from the same working directory. Back up data before switching prototypes, which use different configuration schemas.

## Development status

No automated tests or CI configuration were found. See [IMPROVEMENTS.md](IMPROVEMENTS.md) for correctness issues and proposed validation scenarios.

No repository-level license file was found. Add an explicit license before presenting the project as licensed for reuse.
