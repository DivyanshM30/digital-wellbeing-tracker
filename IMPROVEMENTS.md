# Improvement review

Reviewed on 2026-09-12 through static inspection of tracked main.py and the landing page. Local untracked variants were inspected selectively; main4.py is not a verified replacement.

## Verified GitHub comparison

Live GitHub HEAD is `73234d37e788983555d313a3adba4131bb75f6e2`, matching the cached origin/main reference. GitHub main.py and local main.py share blob `e04adb053e327d897031b930095c78273d97557a`; git diff origin/main -- main.py is empty. Local main3.py hashes to `dc66088ed77c6bfd4c2608271fee5e03a99dc62d`, so it is different. main2.py and main4.py also differ. No branch was merged or application version replaced.

## 1. Fix usage accounting first

Implemented: daily totals now persist in `data/daily_usage.json` with atomic replacement on each tracking sample and final recording on pause/exit. Overview defaults to Today and supports previous recorded dates. Limits use restored daily usage. Monotonic durations are split at local midnight; repeated stop is idempotent. Analytics reads saved totals without appending CSV snapshots.

Missing past days now recover from validated dated text logs at startup, with a backup before migration and no merging into existing dates. Undated cumulative totals and old CSV snapshots are still excluded. Recovered days are marked in History; original logs remain untouched. Window titles are not copied into daily history.

Implemented: 60-second input inactivity cutoff, locked/secure-desktop and disconnected-session checks, and conservative suspend/resume gap rejection. Resume starts a fresh interval; atomic daily storage and midnight splitting are preserved. Regression tests cover idle transitions, lock/unlock, resume, stop, and native-query failures. Existing records remain unchanged.

Remaining: background speech to avoid dropped intervals during long stalls, configurable inactivity grace (including passive media use), native session/power event notifications for transitions shorter than a polling interval, and retention/export controls.

## 2. Make threading and shutdown reliable

Overview redesign update: the tracking worker no longer renders the chart. A single UI timer updates the dashboard, and tray actions are dispatched through a queue. Usage rows are reused; totals follow the selected day or session. The remaining worker lifecycle and alert-thread issues below still need work.

- **UI thread ownership:** dashboard rendering and tray callbacks now run through the main thread. Remaining alert code still reads Tk variables from the tracking worker; replace those reads with synchronized plain-value settings as part of the broader threading fix.
- **Stop/start:** recording and stop now share a lock and final intervals are cleared after saving, preventing duplicate finalization. A stop event wakes the worker. Background speech can still outlive the UI; decouple speech and coordinate full worker shutdown next.
- **Blocking work:** clustering runs synchronously on the GUI thread, and speech runAndWait blocks its caller. Use separate analytics and speech workers and return results through the UI queue.

## 3. Correct settings and limit behavior

- Settings now save on each preference change. Atomic configuration writes and a stable per-user settings location remain useful follow-up work.
- Automatic termination defaults to enabled. Default to reminders, make termination an explicit choice, try graceful closure first, and exclude critical processes and the tracker.
- enforce_limit selects the first matching process name, which may differ from the foreground process in a multi-process app. Retain the intended process identity and handle process exit before enforcement.
- The inline limit form now normalizes names, accepts minute-based durations, and validates 0 < warning < limit. Invalid or duplicate additions show inline feedback.
- Warning state is now keyed by date and app rather than focus changes. Persist warning state or add reminder cooldowns across restarts in a later change.

## 4. Fix insights before expanding the ML

- Total screen time now includes all apps; only the displayed ranking is limited to five.
- Cluster labels are ordered by total usage across every day in a cluster. Larger clusters can look high-usage despite having lower-usage individual days. Order by mean daily usage or an appropriate centroid statistic.
- Handle identical-day data explicitly rather than presenting a single effective cluster as a meaningful low/high comparison.
- schedule_auto_analysis schedules only one invocation. Schedule the next day after completion if automatic daily analysis is intended.
- Prioritize explainable summaries: active time, most-used apps, comparison with complete prior periods, and user-defined limits. Show data coverage and treat clustering as optional exploratory analysis.

## 5. Consolidate the implementation

Choose one canonical version. main2.py, main3.py, and main4.py are untracked locally, so a clone will not include them. main4.py separates storage, idle detection, alerts, and reporting, but its configuration schema differs while sharing config.json. Plan a migration before adopting it.

Its UsageTracker.stop also saves the active interval without clearing the active state; repeated stops need an idempotency check. Treat the prototype as a source of ideas that still needs verification.

Suggested structure:

```text
digital_wellbeing/
  tracking.py       Foreground detection and interval accounting
  storage.py        Persistence and migrations
  limits.py         Threshold rules and enforcement
  alerts.py         Speech and notifications
  analytics.py      Summaries and clustering
  ui.py             Tkinter views and event dispatch
  __main__.py       Startup
tests/              Core and lifecycle regression tests
```

Use transactional interval storage and versioned settings. Store data in a stable per-user application-data directory instead of the current directory. Add periodic checkpoints, optional title recording, retention settings, and export/delete actions.

## 6. Improve repository hygiene and releases

- Add .gitignore for virtual environments, caches, builds, runtime configuration, usage CSVs, logs, databases, and personal shortcuts. Provide sanitized example settings.
- Declare a supported Python version and tested dependency set. Remove the misleading tk pip requirement in favor of Tcl/Tk installation instructions; declare direct imports such as NumPy explicitly.
- Add Windows CI for core tests and packaging smoke checks. Verify the executable on a clean machine.
- Publish a verified Windows release asset. The redesigned landing page removes the .exe.lnk download and provides source setup instructions; packaging remains to be completed.
- Repository links have been corrected to digital-wellbeing-tracker in the redesigned landing page.
- Add a license and release notes. A license claim in a prototype docstring does not establish a repository-level license file.

## Suggested order

1. Select the canonical entry point and add regression tests for accounting, duplicate writes, midnight, and stop/start.
2. Fix persistence and UI/worker boundaries, then settings and enforcement.
3. Correct insight arithmetic with small synthetic datasets.
4. Add data controls, reproducible builds, and a real release; update the landing page to match verified features.

## Validation limits

The py launcher reported no installed Python interpreters. GUI behavior, Python tests, and executable packaging were not run. Documentation was checked against source and repository state; the findings are static code observations, not claims of runtime reproduction or a comprehensive security audit.

## Startup update

Implemented an opt-in current-user Windows sign-in entry. Startup launches begin tracking in the tray, use stable application-relative settings paths, and reveal the window if tray initialization fails. Manual launch behavior and the existing single-instance lock are preserved. Registration and launch-mode tests use mocks without modifying Windows startup configuration.
