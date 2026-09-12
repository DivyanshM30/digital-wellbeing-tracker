# Improvement review

Reviewed on 2026-09-12 through static inspection of tracked main.py and the landing page. Local untracked variants were inspected selectively; main4.py is not a verified replacement.

## Verified GitHub comparison

Live GitHub HEAD is `73234d37e788983555d313a3adba4131bb75f6e2`, matching the cached origin/main reference. GitHub main.py and local main.py share blob `e04adb053e327d897031b930095c78273d97557a`; git diff origin/main -- main.py is empty. Local main3.py hashes to `dc66088ed77c6bfd4c2608271fee5e03a99dc62d`, so it is different. main2.py and main4.py also differ. No branch was merged or application version replaced.

## 1. Fix usage accounting first

**Duplicate history — main.py, analyze_usage and log_daily_usage.** Analysis appends cumulative session snapshots before checking whether insights were already generated. Later analysis sums those rows. Saving 60 seconds, then a cumulative 90 seconds, produces 150 seconds instead of 90. Even a repeated click that reports already-generated insights can append data.

Persist uniquely identified intervals once, independently of analysis, and derive daily totals from them. Alternatively, upsert snapshots keyed by session and date. Test that repeated analysis leaves totals unchanged.

**Daily boundaries and inactivity — track and log_daily_usage.** Limits use session_data, which is not restored as today's total or reset at midnight. CSV logging assigns the entire session to the date of analysis. Restarting loses the session limit baseline; crossing midnight mixes days. Idle and suspend time can also be counted.

Use monotonic time for durations and wall-clock timestamps for reporting. Split intervals at midnight, restore today's totals, and handle idle/lock/suspend. Test restart, midnight, clock changes, and sleep/resume with a fake clock and foreground provider.

**Stale window titles — track.** current_window changes only when the process changes. Switching documents or tabs inside one process retains the old title. Record title changes as new intervals, or omit titles when only app-level statistics are needed.

## 2. Make threading and shutdown reliable

- **UI thread ownership:** track calls gui.update_stats_display directly from the worker; that method changes a Matplotlib/Tk canvas. Tray callbacks also invoke GUI methods. Send events through a queue drained by a main-thread root.after callback.
- **Stop/start races:** GUI-side stop_tracking logs and clears the same state used by the worker, without a join or lock. exit_app can destroy the UI while work continues. Let the worker finalize exactly once after a stop event, then complete shutdown. Test rapid stop/start and exit during alerts.
- **Blocking work:** clustering runs synchronously on the GUI thread, and speech runAndWait blocks its caller. Use separate analytics and speech workers and return results through the UI queue.

## 3. Correct settings and limit behavior

- save_app_settings is called from toggle_theme, but the other preference checkboxes have no save callback and exit_app does not save settings. Changing voice or termination preferences without subsequently toggling the theme can lose those changes on exit. Save on each change and shutdown using atomic replacement; test relaunch.
- Automatic termination defaults to enabled. Default to reminders, make termination an explicit choice, try graceful closure first, and exclude critical processes and the tracker.
- enforce_limit selects the first matching process name, which may differ from the foreground process in a multi-process app. Retain the intended process identity and handle process exit before enforcement.
- Limit dialogs accept negative values and inconsistent thresholds, and manual names are not normalized. Enforce 0 < warning < limit and normalize names.
- Warning state resets on each foreground process change, allowing repeated alerts when returning to an app. Track daily threshold crossings and reminder cooldowns independently of focus.

## 4. Fix insights before expanding the ML

- analyze_usage labels the sum of the top five apps as total screen time. Compute totals across all apps and use the top five only for ranking. Test six or more apps.
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
