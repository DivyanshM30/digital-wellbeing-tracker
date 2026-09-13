# Digital Wellbeing Tracker

A Windows desktop app that tracks time spent in foreground applications, displays usage charts, and provides configurable limits and reminders. Built with Python and Tkinter, with a separate static landing page.

This README describes **main.py**, the entry point currently tracked in Git. The local workspace also contains untracked experimental versions (main2.py, main3.py, and main4.py) with different features and configuration formats.

## Verified source version

GitHub HEAD was checked during this review: commit `73234d37e788983555d313a3adba4131bb75f6e2`. Its `main.py` matches local `main.py` exactly under Git's content hashing (blob `e04adb053e327d897031b930095c78273d97557a`). Local `main3.py` has different content; it is not the current GitHub entry point. The local branch is one commit ahead and one behind the remote, but their `main.py` content matches.

## Features

- Foreground process and window-title monitoring, sampled roughly once per second. Tracking automatically pauses after 60 seconds without input, on lock/secure desktops, and for disconnected Windows sessions.
- Overview with Start/Pause controls, a Today/history selector, reusable application rows, and a horizontal usage chart. Daily totals survive restart; an optional This session view shows the current run.
- History with daily/weekly totals, a seven-day chart, previous/next date navigation, and a scrollable breakdown of every recorded app. Select an app to explore its trend.
- Sidebar navigation, matching light/dark themes throughout, and an inline App Limits editor with durations entered in minutes (stored as seconds).
- Voice alerts, desktop notifications, and optional application termination.
- Light/dark themes and system-tray controls.
- Local JSON settings and atomic daily usage history, saved during tracking and on pause/exit.
- Smart Insights using pandas and scikit-learn K-means clustering, requiring at least three dates of usage. These are statistical summaries, not an external AI service.

**Current limitations:** the first 60 seconds without keyboard or mouse input count as usage. Passive reading or video playback pauses after that grace period. Older saved and recovered records may still include unattended time; they are not rewritten. Old undated cumulative totals and potentially duplicated CSV snapshots are not automatically imported into daily history. See [the improvement review](IMPROVEMENTS.md).

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
3. In **App Limits**, use **Find running apps** or enter a process name such as `chrome.exe`. Enter minutes: for example, a 60-minute daily limit and a warning after 48 minutes. Click **Save limit**. Select a row to edit it; use **New limit** to start another form. The list shows durations as HH:MM:SS.
4. Switch applications and view the Overview. **Today** combines usage across restarts, and the date selector lets you revisit recorded days. **This session** covers the current run only. Select **Pause Tracking** to pause collection.
5. Use **Insights → Analyze usage** after collecting at least three dates of new daily history. Analysis reads saved daily totals without appending duplicate snapshots.
6. Closing the window hides it when minimizing to the tray is enabled; tracking can continue. Use the tray's exit action to quit.

## Data and privacy

### Browse your history

Open **History** in the sidebar and choose **Daily** or **Weekly**. Use Previous/Next, Today, Yesterday, or enter a date as `YYYY-MM-DD` and press Enter or Go. Weeks run Monday through Sunday. Future dates cannot be selected. Dates and durations are shown in readable form, and app-specific filters are explicitly labeled.

The chart shows the week containing the selected date. Click a day's bar to open its daily breakdown. The table includes all recorded apps, sorted by duration, with their percentage of the entire selected period. Selecting a row filters the summary and chart to that app; **Show all apps** restores the overall view.

Weekly averages divide recorded usage by elapsed calendar days in the selected week (seven for completed weeks). Missing records are labeled **No data**, and future days are marked separately; an unrecorded day is not proof of zero screen use. The current day is partial while tracking continues. Saved history works immediately without a data migration. Hourly timelines are not available because history currently stores daily totals only.

### Idle, lock, and resume behavior

Tracking keeps the first 60 seconds of inactivity, then stops counting until input returns. Overview displays an automatic pause status. Unlocking or returning from idle starts a fresh interval, without filling the unattended gap. Daily history, session totals, and app limits use these filtered durations.

A polling gap longer than five seconds, or a wall/monotonic clock discrepancy greater than two seconds, is discarded to exclude suspend time. This conservative rule also drops long stalls such as blocking speech alerts. Windows input and session queries must succeed to count usage. Lock transitions discard the pending sample; very short lock/suspend events entirely between polls can escape detection. No existing history is recalculated, because daily totals do not contain enough information to reconstruct attendance.

Regression tests use simulated input/session states and clocks; they never lock or suspend the computer:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Local files

The desktop implementation stores data locally in plain-text files:

| Path | Purpose |
| --- | --- |
| `config.json` | Limits, warning thresholds, and cumulative usage |
| `app_settings.json` | UI and alert preferences; saved whenever a setting changes |
| `data/daily_usage.json` | Per-date, per-application totals in seconds; authoritative daily history |
| `data/tracker.lock` | Prevents a second running app instance from overwriting history |
| `logs/YYYY-MM-DD.log` | Legacy window-title logs; retained but no longer written by this version |
| `usage_log.csv` | Legacy analysis snapshots; retained but no longer used for new insights |
| `error_log.txt` | Analysis errors |

Daily history is saved in the `data` directory beside `main.py`, independent of the launch directory. Durations use a monotonic clock and intervals are split at local midnight. Each tracking sample is committed through an atomic file replacement; pause and exit save the final fraction of an interval. Abrupt termination can still lose the interval since the last successful sample, especially during a blocking speech alert. Only one instance can run at a time.

At startup, valid dated `logs/YYYY-MM-DD.log` files recover missing past days into daily history. Existing daily records and the current day are never merged or overwritten. Malformed files and implausible totals are skipped. Before recovery changes an existing history file, a copy is saved as `data/daily_usage.before-legacy-import.json`. History labels recovered periods; original logs remain untouched. Fully exit the tray app and restart to run recovery after upgrading.

Undated totals and potentially duplicated CSV snapshots cannot be reliably reconstructed and are not imported. Recovered totals reflect what older logs recorded, including their existing tracking limitations. Window titles remain in memory during a run and are not copied into the daily file. Legacy logs may contain document or browser page names. There is no retention or deletion UI; exit the app before backing up or removing data.

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
- **No insights:** at least three recorded dates must exist in `data/daily_usage.json`; old CSV snapshots are not imported automatically.
- **Window disappears:** check the Windows notification area for the tray icon.
- **Different settings or totals:** launch from the same working directory. Back up data before switching prototypes, which use different configuration schemas.

## Development status

Run the focused Overview regression tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

These checks cover summaries, paused totals, limit states, row reuse, the UI timer, restart persistence, midnight splits, repeated stop, failed writes, and limit-form validation without starting monitoring. They do not replace a Windows visual check. The app starts at 1260 × 860 with a minimum window size of 1180 × 820; charts refresh every five seconds and usage rows every second.

Insights shows recorded-day coverage and enables analysis after three recorded dates. Settings groups Appearance, Notifications, App Limits, and Data information; preference changes save automatically.

Dropdowns use matching light/dark popup colors and larger text. The date picker displays readable calendar dates and retains your selection during refreshes. In App Limits, refresh the running-app list, type to filter it, and use the arrow keys to browse. Enter in the app field moves to the duration; Enter in a duration field saves. Choosing an existing app opens its limit for editing, and saving keeps the row selected. Refreshing the app list preserves your draft. Insights can be refreshed again on the same day.

CI is not configured. See [IMPROVEMENTS.md](IMPROVEMENTS.md) for remaining correctness issues and proposed validation scenarios.

No repository-level license file was found. Add an explicit license before presenting the project as licensed for reuse.
