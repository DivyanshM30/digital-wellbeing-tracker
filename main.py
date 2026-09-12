import os
import time
import json
import math
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import psutil
import win32gui
import win32process
import pyttsx3
from collections import defaultdict
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import queue
import sys
import pystray
from PIL import Image, ImageDraw
from plyer import notification
import sv_ttk   
import pandas as pd
from sklearn.cluster import KMeans

class DailyUsageStore:
    """Daily totals committed atomically, independent of analytics or shutdown."""

    def __init__(self, path=None):
        application_path = sys.executable if getattr(sys, 'frozen', False) else __file__
        self.path = Path(path) if path else Path(application_path).resolve().parent / 'data' / 'daily_usage.json'
        self.lock = threading.RLock()
        self.days = {}
        if self.path.exists():
            payload = json.loads(self.path.read_text(encoding='utf-8'))
            if payload.get('version') != 1:
                raise ValueError('Unsupported daily usage version; file left unchanged')
            for day, apps in payload['days'].items():
                datetime.strptime(day, '%Y-%m-%d')
                if not isinstance(apps, dict) or any(
                        not isinstance(app, str) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value < 0 for app, value in apps.items()):
                    raise ValueError('Invalid daily usage data; file left unchanged')
            self.days = payload['days']

    def record(self, app, started, seconds):
        if not math.isfinite(seconds):
            raise ValueError('Usage duration must be finite')
        if seconds <= 0:
            return
        with self.lock:
            updated = {day: apps.copy() for day, apps in self.days.items()}
            cursor = datetime.fromtimestamp(started)
            remaining = seconds
            while remaining > 0:
                midnight = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
                part = min(remaining, (midnight - cursor).total_seconds())
                apps = updated.setdefault(cursor.date().isoformat(), {})
                apps[app] = apps.get(app, 0) + part
                remaining -= part
                cursor = midnight
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                        prefix='.daily-', suffix='.tmp', delete=False) as output:
                    temporary = output.name
                    json.dump({'version': 1, 'days': updated}, output, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self.path)
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            self.days = updated

    def usage(self, day):
        with self.lock:
            return self.days.get(day, {}).copy()

    def dates(self):
        with self.lock:
            return sorted(self.days, reverse=True)

    def rows(self):
        with self.lock:
            return [{'date': day, 'app': app, 'duration': seconds}
                    for day, apps in sorted(self.days.items()) for app, seconds in apps.items()]


class DigitalWellnessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Wellness Tracker")
        self.root.geometry("1260x860")
        self.root.minsize(1180, 820)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tracking_active = False
        self.tracking_thread = None
        self.ui_actions = queue.Queue()
        self.closing = False
        self.ui_timer = None
        self.last_chart_refresh = 0
        self.dark_mode = tk.BooleanVar(value=False)
        
        self.tracker = ScreenTimeTracker(self)
        self.insights_generated_for = None
        self.create_widgets()
        
        self.setup_system_tray()

        self.toggle_theme()
        
        self.schedule_auto_analysis()
        self.update_ui()

    def create_widgets(self):
        self.app_shell = ttk.Frame(self.root)
        self.app_shell.pack(fill="both", expand=True)
        self.app_shell.columnconfigure(1, weight=1)
        self.app_shell.rowconfigure(0, weight=1)
        self.notebook = ttk.Notebook(self.app_shell, style="Navigation.TNotebook")
        self.notebook.grid(row=0, column=1, sticky="nsew")
        
        self.dashboard_frame = ttk.Frame(self.notebook, style="Overview.TFrame")
        self.notebook.add(self.dashboard_frame, text="Overview")
        self.build_overview()

        self.build_remaining_pages()
        self.build_sidebar()

        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.load_app_settings()
        self.update_limits_display()

    def ui_frame(self, parent, surface="paper", **kwargs):
        widget = tk.Frame(parent, **kwargs)
        self.overview_widgets.append((widget, {"background": surface}))
        return widget

    def ui_label(self, parent, text, size=11, surface="paper", color="ink", **kwargs):
        widget = tk.Label(parent, text=text, anchor="w", font=("Segoe UI", size), **kwargs)
        self.overview_widgets.append((widget, {"background": surface, "foreground": color}))
        return widget

    def page_header(self, parent, eyebrow, title, description):
        header = self.ui_frame(parent)
        header.pack(fill="x", padx=26, pady=(22, 20))
        self.ui_label(header, eyebrow, 9, color="muted").pack(anchor="w")
        self.ui_label(header, title, 27).pack(anchor="w", pady=(5, 4))
        self.ui_label(header, description, 11, color="muted",
                      wraplength=650, justify="left").pack(anchor="w")

    def build_remaining_pages(self):
        self.limits_frame = ttk.Frame(self.notebook, style="Overview.TFrame")
        self.smart_frame = ttk.Frame(self.notebook, style="Overview.TFrame")
        self.settings_frame = ttk.Frame(self.notebook, style="Overview.TFrame")
        for page, title in ((self.limits_frame, "App Limits"), (self.smart_frame, "Insights"),
                            (self.settings_frame, "Settings")):
            self.notebook.add(page, text=title)
        self.build_limits_page()
        self.build_insights_page()
        self.build_settings_page()

    def build_sidebar(self):
        sidebar = self.ui_frame(self.app_shell, "card", width=170)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False)
        self.ui_label(sidebar, "dw", 32, "card", "accent").pack(anchor="w", padx=20, pady=(24, 0))
        self.ui_label(sidebar, "digital wellbeing", 11, "card").pack(anchor="w", padx=20)
        self.ui_label(sidebar, "A little more intentional.", 9, "card", "muted").pack(anchor="w", padx=20, pady=(4, 30))
        self.nav_buttons = []
        for index, name in enumerate(("Overview", "App Limits", "Insights", "Settings")):
            button = ttk.Button(sidebar, text=name, command=lambda i=index: self.notebook.select(i))
            button.pack(fill="x", padx=12, pady=5)
            self.nav_buttons.append(button)
        self.ui_label(sidebar, "Windows desktop\nStored on your device", 9, "card", "muted",
                      justify="left").pack(side="bottom", anchor="w", padx=20, pady=24)
        self.notebook.bind("<<NotebookTabChanged>>", self.navigation_changed)

    def navigation_changed(self, event=None):
        selected = self.notebook.index(self.notebook.select())
        for index, button in enumerate(self.nav_buttons):
            button.configure(style="Selected.TButton" if index == selected else "TButton")
        self.refresh_insight_coverage()

    def build_limits_page(self):
        self.page_header(self.limits_frame, "YOUR OWN BOUNDARIES", "App Limits",
                         "Set a daily allowance and choose when you would like a reminder.")
        body = self.ui_frame(self.limits_frame)
        body.pack(fill="both", expand=True, padx=26, pady=(0, 22))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0, minsize=275)
        body.rowconfigure(0, weight=1)
        list_card = self.ui_frame(body, "card", padx=14, pady=16)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.ui_label(list_card, "Your daily limits", 15, "card").pack(anchor="w", pady=(0, 12))
        table = self.ui_frame(list_card, "card")
        table.pack(fill="both", expand=True)
        self.limits_tree = ttk.Treeview(table, columns=("app", "limit", "warning"),
                                        show="headings", selectmode="browse", height=12)
        for name, title, width in (("app", "Application", 145), ("limit", "Daily limit", 95),
                                    ("warning", "Warn at", 95)):
            self.limits_tree.heading(name, text=title)
            self.limits_tree.column(name, width=width, minwidth=65)
        scrollbar = ttk.Scrollbar(table, command=self.limits_tree.yview)
        self.limits_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.limits_tree.pack(fill="both", expand=True)
        self.limits_tree.bind("<<TreeviewSelect>>", self.edit_app_limit)
        self.limits_empty = self.ui_label(list_card, "No limits yet. Add your first app using the form.", 10,
                                           "card", "muted", wraplength=300, justify="left")
        self.limits_empty.pack(anchor="w", pady=(12, 0))
        actions = self.ui_frame(list_card, "card")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="New limit", command=self.add_app_limit).pack(side="left")
        self.remove_limit_button = ttk.Button(actions, text="Remove selected", command=self.remove_app_limit, state="disabled")
        self.remove_limit_button.pack(side="left", padx=8)
        editor = self.ui_frame(body, "card", padx=18, pady=16)
        editor.grid(row=0, column=1, sticky="nsew")
        self.limit_editor_title = self.ui_label(editor, "Add an application", 15, "card")
        self.limit_editor_title.pack(anchor="w", pady=(0, 18))
        self.limit_app_var = tk.StringVar()
        self.limit_minutes_var = tk.StringVar(value="60")
        self.warning_minutes_var = tk.StringVar(value="48")
        self.editing_limit = None
        self.ui_label(editor, "Process name", 10, "card").pack(anchor="w")
        self.app_choices = []
        self.limit_app_entry = ttk.Combobox(editor, textvariable=self.limit_app_var, width=24,
                                           height=8, font=("Segoe UI", 11), style="Wellbeing.TCombobox")
        self.limit_app_entry.bind("<KeyRelease>", self.filter_app_choices)
        self.limit_app_entry.bind("<<ComboboxSelected>>", self.select_app_choice)
        self.limit_app_entry.pack(fill="x", pady=(5, 4))
        self.ui_label(editor, "For example: chrome.exe", 9, "card", "muted").pack(anchor="w")
        ttk.Button(editor, text="Find running apps", command=self.detect_active_apps).pack(fill="x", pady=(12, 18))
        self.duration_entries = []
        for title, variable in (("Daily limit · minutes", self.limit_minutes_var),
                                ("Warn after · minutes", self.warning_minutes_var)):
            self.ui_label(editor, title, 10, "card").pack(anchor="w")
            entry = ttk.Entry(editor, textvariable=variable)
            entry.pack(fill="x", pady=(5, 15))
            entry.bind('<Return>', lambda event: self.save_limit_form())
            self.duration_entries.append(entry)
        self.limit_form_message = self.ui_label(editor, "", 10, "card", "muted",
                                                wraplength=230, justify="left")
        self.limit_form_message.pack(anchor="w", pady=(0, 12))
        self.save_limit_button = ttk.Button(editor, text="Save limit", command=self.save_limit_form)
        self.save_limit_button.pack(fill="x")
        editor.bind("<Return>", lambda event: self.save_limit_form())
        self.limit_app_entry.bind("<Return>", self.focus_limit_duration)
        self.ui_label(editor, "Type to filter · ↓ to browse · Esc to close", 9, "card", "muted",
                      wraplength=230, justify="left").pack(anchor="w", pady=(10, 0))
        self.ui_label(editor, "Alerts and automatic app closure can be changed in Settings.",
                      10, "card", "muted", wraplength=230, justify="left").pack(anchor="w", pady=(20, 0))

    @staticmethod
    def parse_limit_form(app, limit_minutes, warning_minutes):
        name = app.strip().lower()
        if not name:
            raise ValueError("Enter a process name, such as chrome.exe.")
        try:
            limit_value, warning_value = float(limit_minutes), float(warning_minutes)
            if not math.isfinite(limit_value) or not math.isfinite(warning_value):
                raise ValueError()
            limit, warning = round(limit_value * 60), round(warning_value * 60)
        except (ValueError, OverflowError):
            raise ValueError("Enter valid durations in minutes.") from None
        if not 0 < warning < limit:
            raise ValueError("The warning must be greater than zero and earlier than the limit.")
        return name, limit, warning

    def save_limit_form(self):
        try:
            app, limit, warning = self.parse_limit_form(
                self.limit_app_var.get(), self.limit_minutes_var.get(), self.warning_minutes_var.get())
        except ValueError as error:
            self.limit_form_message.config(text=str(error))
            return
        if self.editing_limit is None and app in self.tracker.app_limits:
            self.limit_form_message.config(text="This app already has a limit. Select it in the list to edit.")
            return
        previous_limits = self.tracker.app_limits.copy()
        previous_warnings = self.tracker.warning_times.copy()
        self.tracker.app_limits[app] = limit
        self.tracker.warning_times[app] = warning
        try:
            self.tracker.save_config()
        except OSError as error:
            self.tracker.app_limits = previous_limits
            self.tracker.warning_times = previous_warnings
            self.limit_form_message.config(text=f"Could not save: {error}")
            return
        self.update_limits_display()
        self.limits_tree.selection_set(app)
        self.limits_tree.see(app)
        self.edit_app_limit()
        self.limit_form_message.config(text=f"Saved daily limit for {app}.")

    def filter_app_choices(self, event=None):
        if self.editing_limit is not None or (event and event.keysym in (
                'Up', 'Down', 'Return', 'Escape', 'Tab')):
            return
        query = self.limit_app_var.get().strip().lower()
        matches = [name for name in self.app_choices if query in name]
        self.limit_app_entry.configure(values=matches)
        self.limit_form_message.configure(text=(f'{len(matches)} matching apps. Use ↓ to browse.'
            if matches else 'No matching running app. You can still save the typed process name.'))

    def select_app_choice(self, event=None):
        name = self.limit_app_var.get().strip().lower()
        if name in self.tracker.app_limits:
            self.limits_tree.selection_set(name)
            self.limits_tree.see(name)
            self.edit_app_limit()
        else:
            self.limit_form_message.configure(text=f'Ready to set a daily limit for {name}.')

    def focus_limit_duration(self, event=None):
        self.select_app_choice()
        self.duration_entries[0].focus_set()
        return 'break'

    def build_insights_page(self):
        self.page_header(self.smart_frame, "PAUSE AND REFLECT", "Insights",
                         "Understand your patterns, one day at a time. Summaries use your saved daily history.")
        card = self.ui_frame(self.smart_frame, "card", padx=22, pady=20)
        card.pack(fill="both", expand=True, padx=26, pady=(0, 24))
        toolbar = self.ui_frame(card, "card")
        toolbar.pack(fill="x", pady=(0, 20))
        self.insight_coverage = self.ui_label(toolbar, "Building your history", 12, "card")
        self.insight_coverage.pack(side="left")
        self.analyze_button = ttk.Button(toolbar, text="Analyze usage", command=self.analyze_usage)
        self.analyze_button.pack(side="right")
        self.recommendation_text = tk.Text(card, wrap="word", font=("Segoe UI", 12),
                                           relief="flat", borderwidth=0, padx=12, pady=14,
                                           height=12, spacing1=4, spacing3=8)
        self.overview_widgets.append((self.recommendation_text, {
            "background": "paper", "foreground": "ink", "insertbackground": "ink",
            "selectbackground": "accent", "selectforeground": "button_text"}))
        scroll = ttk.Scrollbar(card, command=self.recommendation_text.yview)
        self.recommendation_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.recommendation_text.pack(fill="both", expand=True)
        self.recommendation_text.insert("1.0", "A clearer picture takes a little time.\n\n"
            "Record usage on at least three different days to unlock your first analysis.\n\n"
            "In the meantime, explore Today and previous days in Overview.\n\n"
            "These are statistical summaries of foreground time. Idle time is currently included.")
        self.recommendation_text.configure(state="disabled")

    def refresh_insight_coverage(self):
        days = len(self.tracker.daily_store.dates())
        self.insight_coverage.configure(text=f"{days} recorded day{'s' if days != 1 else ''} · "
                                       + ("Ready to explore" if days >= 3 else f"{3 - days} more needed"))
        self.analyze_button.configure(state="normal" if days >= 3 else "disabled")

    def build_settings_page(self):
        self.page_header(self.settings_frame, "MAKE IT YOURS", "Settings",
                         "Choose how the tracker fits into your day. Changes are saved automatically.")
        self.voice_alerts_var = tk.BooleanVar(value=True)
        self.auto_shutdown_var = tk.BooleanVar(value=True)
        self.tray_notifications_var = tk.BooleanVar(value=True)
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        body = self.ui_frame(self.settings_frame)
        body.pack(fill="both", expand=True, padx=26, pady=(0, 22))
        for column in (0, 1):
            body.columnconfigure(column, weight=1, uniform="settings")
        groups = (
            ("Appearance", (("Dark mode", "A softer palette for low-light spaces.", self.dark_mode, self.toggle_theme),
                            ("Minimize to tray", "Closing the window keeps the app available in the notification area.",
                             self.minimize_to_tray_var, self.save_app_settings))),
            ("Notifications", (("Voice reminders", "Hear a reminder when you approach a limit.", self.voice_alerts_var, self.save_app_settings),
                               ("Desktop notifications", "Show updates in the Windows notification area.", self.tray_notifications_var, self.save_app_settings))),
            ("App limits", (("Close apps at their limit", "Can close an app with unsaved work. Turn off for reminders only.",
                            self.auto_shutdown_var, self.save_app_settings),)),
        )
        for index, (title, settings) in enumerate(groups):
            card = self.ui_frame(body, "card", padx=18, pady=18)
            card.grid(row=index // 2, column=index % 2, sticky="nsew",
                      padx=(0, 8) if index % 2 == 0 else (8, 0), pady=(0, 16))
            self.ui_label(card, title, 15, "card").pack(anchor="w", pady=(0, 12))
            for name, description, variable, command in settings:
                toggle = tk.Checkbutton(card, text=name, variable=variable, command=command,
                                         font=("Segoe UI", 11), anchor="w", relief="flat",
                                         borderwidth=0, highlightthickness=0, cursor="hand2")
                self.overview_widgets.append((toggle, {"background": "card", "foreground": "ink",
                    "activebackground": "card", "activeforeground": "ink", "selectcolor": "paper"}))
                toggle.pack(fill="x", pady=(4, 4))
                self.ui_label(card, description, 10, "card", "muted", wraplength=270,
                              justify="left").pack(anchor="w", padx=(22, 0), pady=(0, 12))
        data = self.ui_frame(body, "card", padx=18, pady=18)
        data.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(0, 16))
        self.ui_label(data, "Your data", 15, "card").pack(anchor="w", pady=(0, 12))
        self.ui_label(data, "Saved on this device", 11, "card").pack(anchor="w")
        self.ui_label(data, "Daily totals are saved automatically and survive restart. "
                      "Window titles are not written to daily history.\n\n"
                      "There is no automatic deletion. Back up your data before removing files.",
                      10, "card", "muted", wraplength=280, justify="left").pack(anchor="w", pady=(8, 0))

    def build_overview(self):
        """Build a dashboard whose widgets survive each tracking refresh."""
        self.day_var = tk.StringVar(value='Today')
        self.overview_widgets = []
        self.overview_rows = []
        self.dashboard_frame.columnconfigure(0, weight=1)
        self.dashboard_frame.rowconfigure(3, weight=1)

        def frame(parent, surface="paper", **kwargs):
            widget = tk.Frame(parent, **kwargs)
            self.overview_widgets.append((widget, {"background": surface}))
            return widget

        def label(parent, text="", size=11, surface="paper", color="ink", **kwargs):
            widget = tk.Label(parent, text=text, font=("Segoe UI", size),
                              anchor="w", **kwargs)
            self.overview_widgets.append(
                (widget, {"background": surface, "foreground": color}))
            return widget

        heading = frame(self.dashboard_frame)
        heading.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 14))
        self.day_lookup = {}
        self.day_choices = None
        period = frame(heading)
        period.pack(side='right', anchor='n')
        label(period, 'View usage', 9, color='muted').pack(anchor='w', pady=(0, 5))
        self.day_picker = ttk.Combobox(period, textvariable=self.day_var, state='readonly',
                                       values=('Today', 'This session'), width=23, height=8,
                                       font=('Segoe UI', 11), style='Wellbeing.TCombobox')
        self.day_picker.pack(anchor='w')
        self.day_picker.bind('<<ComboboxSelected>>', self.change_usage_day)
        label(heading, "YOUR TIME, WITH INTENTION", 9, color="muted").pack(anchor="w")
        label(heading, "Overview", 27).pack(anchor="w", pady=(4, 0))
        label(heading, "A little awareness goes a long way.", 11,
              color="muted").pack(anchor="w")

        tracking = frame(self.dashboard_frame, "card", padx=18, pady=14)
        tracking.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 14))
        tracking.columnconfigure(0, weight=1)
        self.tracking_badge = label(tracking, "READY TO BEGIN", 9, "card", "accent")
        self.tracking_badge.grid(row=0, column=0, sticky="w")
        self.current_app_label = label(tracking, "Make a little room for yourself.", 14, "card")
        self.current_app_label.grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.current_window_label = label(tracking, "Start tracking to see your application usage.",
                                          10, "card", "muted")
        self.current_window_label.grid(row=2, column=0, sticky="w", pady=(3, 0))
        self.start_stop_button = tk.Button(
            tracking, text="Start Tracking", command=self.toggle_tracking,
            font=("Segoe UI", 11, "bold"), relief="flat", borderwidth=0,
            padx=22, pady=12, cursor="hand2")
        self.overview_widgets.append((self.start_stop_button, {
            "background": "accent", "foreground": "button_text",
            "activebackground": "ink", "activeforeground": "paper"}))
        self.start_stop_button.grid(row=0, column=1, rowspan=3, padx=(15, 0))

        summaries = frame(self.dashboard_frame)
        summaries.grid(row=2, column=0, sticky="ew", padx=26, pady=(0, 16))
        self.summary_values = []
        self.summary_details = []
        for column, (title, value, detail) in enumerate((
                ("SELECTED PERIOD", "00:00:00", "Foreground time · includes idle time"),
                ("MOST USED", "—", "Your most-used app will appear here"),
                ("LIMIT CHECK-IN", "0 apps", "Approaching or over their limit"))):
            summaries.columnconfigure(column, weight=1, uniform="summary")
            card = frame(summaries, "card", padx=14, pady=12)
            card.grid(row=0, column=column, sticky="nsew",
                      padx=(0 if column == 0 else 5, 0 if column == 2 else 5))
            label(card, title, 9, "card", "muted").pack(anchor="w")
            number = label(card, value, 20, "card")
            number.pack(anchor="w", pady=(6, 4))
            caption = label(card, detail, 9, "card", "muted", wraplength=235,
                            justify="left")
            caption.pack(anchor="w")
            self.summary_values.append(number)
            self.summary_details.append(caption)

        body = frame(self.dashboard_frame)
        body.grid(row=3, column=0, sticky="nsew", padx=26, pady=(0, 12))
        body.columnconfigure(0, weight=1, uniform="body")
        body.columnconfigure(1, weight=1, uniform="body")
        body.rowconfigure(0, weight=1)
        self.progress_frame = frame(body, "card", padx=16, pady=14)
        self.progress_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        label(self.progress_frame, "Application activity", 14, "card").pack(anchor="w")
        label(self.progress_frame, "Top 5 · Bars show share of period or limit used",
              9, "card", "muted", wraplength=350, justify="left").pack(anchor="w", pady=(3, 10))
        self.empty_usage = label(self.progress_frame,
            "A fresh start.\n\nStart tracking, then switch between apps.\nYour session will take shape here.",
            11, "card", "muted", justify="left", wraplength=320)
        self.empty_usage.pack(anchor="w", pady=25)
        for _ in range(5):
            row = frame(self.progress_frame, "card")
            top = frame(row, "card")
            top.pack(fill="x")
            name = label(top, "", 10, "card")
            name.pack(side="left")
            duration = label(top, "", 10, "card", "muted")
            duration.pack(side="right")
            bar = tk.Canvas(row, height=5, highlightthickness=0, borderwidth=0)
            self.overview_widgets.append((bar, {"background": "track"}))
            fill = bar.create_rectangle(0, 0, 0, 5, width=0)
            bar.pack(fill="x", pady=(6, 3))
            detail = label(row, "", 9, "card", "muted")
            detail.pack(anchor="w")
            item = {"frame": row, "name": name, "duration": duration,
                    "bar": bar, "fill": fill, "detail": detail, "fraction": 0, "color": "accent"}
            bar.bind("<Configure>", lambda event, item=item: self.paint_usage_bar(item))
            self.overview_rows.append(item)

        self.stats_frame = frame(body, "card", padx=10, pady=14)
        self.stats_frame.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        label(self.stats_frame, "Where your time goes", 14, "card").pack(anchor="w", padx=6)
        label(self.stats_frame, "Top 5 applications · minutes in selected period", 9,
              "card", "muted").pack(anchor="w", padx=6, pady=(3, 0))
        self.figure = plt.Figure(figsize=(4, 2.8), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.stats_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        label(self.dashboard_frame,
              "Daily totals are saved automatically. Choose a date to revisit previous days. Idle time is included.",
              9, color="muted").grid(row=4, column=0, sticky="w", padx=26, pady=(0, 12))

    def overview_usage(self):
        """Snapshot session values without adding empty entries to tracker state."""
        selection = self.day_var.get() if hasattr(self, 'day_var') else 'This session'
        if selection != 'This session':
            day = datetime.now().date().isoformat() if selection == 'Today' else getattr(self, 'day_lookup', {}).get(selection, selection)
            usage = self.tracker.daily_store.usage(day)
            return dict(sorted(usage.items(), key=lambda item: (-item[1], item[0])))
        usage = {app: max(0, data["time"])
                 for app, data in self.tracker.session_data.copy().items()}
        current_app = self.tracker.current_app
        started = self.tracker.start_time
        if self.tracking_active and current_app and started is not None:
            usage[current_app] = usage.get(current_app, 0) + max(0, time.time() - started)
        return dict(sorted(((app, seconds) for app, seconds in usage.items() if seconds > 0),
                           key=lambda item: (-item[1], item[0])))

    def change_usage_day(self, event=None):
        usage = self.overview_usage()
        self.update_progress_bars(usage)
        self.update_stats_display(usage)
        self.last_chart_refresh = time.monotonic()

    def refresh_day_choices(self):
        today = datetime.now().date().isoformat()
        dates = tuple(day for day in self.tracker.daily_store.dates() if day != today)
        key = (today, dates)
        if key == self.day_choices:
            return
        selected = self.day_var.get()
        selected_date = self.day_lookup.get(selected, selected)
        self.day_lookup = {datetime.strptime(day, '%Y-%m-%d').strftime('%a, %d %b %Y'): day
                           for day in dates}
        self.day_picker.configure(values=['Today', 'This session'] + list(self.day_lookup))
        if selected not in ('Today', 'This session'):
            label = next((label for label, day in self.day_lookup.items() if day == selected_date), 'Today')
            self.day_var.set(label)
        self.day_choices = key

    def tracking_finished(self):
        if self.tracking_thread and self.tracking_thread.is_alive():
            return
        self.tracking_active = False
        self.start_stop_button.config(text='Start Tracking')
        self.status_bar.config(text='Tracking paused · daily totals saved')
        self.last_chart_refresh = 0

    @staticmethod
    def short_app_name(app, length=24):
        name = app[:-4] if app.lower().endswith(".exe") else app
        return name if len(name) <= length else name[:length - 1] + "…"

    def paint_usage_bar(self, row):
        if not hasattr(self, "palette"):
            return
        row["bar"].coords(row["fill"], 0, 0,
                          row["bar"].winfo_width() * row["fraction"], 5)
        row["bar"].itemconfigure(row["fill"], fill=self.palette[row["color"]])

    def load_app_settings(self):
        """Load application settings"""
        try:
            if os.path.exists('app_settings.json'):
                with open('app_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.dark_mode.set(settings.get('dark_mode', False))
                    self.voice_alerts_var.set(settings.get('voice_alerts', True))
                    self.auto_shutdown_var.set(settings.get('auto_shutdown', True))
                    self.tray_notifications_var.set(settings.get('tray_notifications', True))
                    self.minimize_to_tray_var.set(settings.get('minimize_to_tray', True))
        except Exception as e:
            print(f"Error loading app settings: {e}")

    def save_app_settings(self):
        """Save application settings"""
        settings = {
            'dark_mode': self.dark_mode.get(),
            'voice_alerts': self.voice_alerts_var.get(),
            'auto_shutdown': self.auto_shutdown_var.get(), 
            'tray_notifications': self.tray_notifications_var.get(),
            'minimize_to_tray': self.minimize_to_tray_var.get()
        }
        try:
            with open('app_settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving app settings: {e}")
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(text=f'Settings could not be saved: {e}')

    def toggle_theme(self):
        """Apply the same quiet palette to the dashboard and its chart."""
        sv_ttk.set_theme("dark" if self.dark_mode.get() else "light")
        self.palette = ({
            "paper": "#202b25", "card": "#2b3830", "ink": "#eef2e7",
            "muted": "#b7c4b7", "accent": "#b4cc95", "track": "#465447",
            "warning": "#e1b768", "danger": "#eb9387", "button_text": "#202b25",
        } if self.dark_mode.get() else {
            "paper": "#f6f5ef", "card": "#ffffff", "ink": "#263c32",
            "muted": "#607062", "accent": "#526f43", "track": "#e6ebdf",
            "warning": "#a87526", "danger": "#b95343", "button_text": "#ffffff",
        })
        style = ttk.Style()
        style.layout("Navigation.TNotebook.Tab", [])
        style.configure("Navigation.TNotebook", borderwidth=0, background=self.palette["paper"])
        style.configure("Overview.TFrame", background=self.palette["paper"])
        style.configure("Treeview", rowheight=36)
        style.configure("Selected.TButton", foreground=self.palette["accent"], font=("Segoe UI", 11, "bold"))
        style.configure('Wellbeing.TCombobox', padding=(10, 8), arrowsize=16)
        style.map('Wellbeing.TCombobox', fieldbackground=[('readonly', self.palette['card'])],
                  foreground=[('readonly', self.palette['ink'])],
                  selectbackground=[('readonly', self.palette['accent'])],
                  selectforeground=[('readonly', self.palette['button_text'])])
        # ttk popdowns are native Tcl listboxes rather than Python child widgets.
        for combo in (self.day_picker, self.limit_app_entry):
            popup = self.root.tk.call('ttk::combobox::PopdownWindow', str(combo))
            self.root.tk.call(str(popup) + '.f.l', 'configure',
                '-background', self.palette['card'], '-foreground', self.palette['ink'],
                '-selectbackground', self.palette['accent'], '-selectforeground', self.palette['button_text'],
                '-font', ('Segoe UI', 11), '-borderwidth', 0)
        for widget, options in self.overview_widgets:
            widget.configure(**{key: self.palette[value] for key, value in options.items()})
        self.canvas.get_tk_widget().configure(background=self.palette["card"], highlightthickness=0)
        self.update_progress_bars()
        self.update_stats_display()
        self.save_app_settings()


    def setup_system_tray(self):
        """Setup the system tray icon and menu"""
        icon_image = self.create_tray_icon()
        
        menu_items = (
            pystray.MenuItem('Show', lambda icon, item: self.ui_actions.put(self.show_window)),
            pystray.MenuItem('Start/Stop Tracking', lambda icon, item: self.ui_actions.put(self.toggle_tracking_from_tray)),
            pystray.MenuItem('Exit', lambda icon, item: self.ui_actions.put(self.exit_app))
        )
        
        self.tray_icon = pystray.Icon("digital_wellness", icon_image, "Digital Wellness", menu_items)
        
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def create_tray_icon(self, size=64):
        """Create a simple icon for the system tray"""
        image = Image.new('RGB', (size, size), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        margin = size // 8
        draw.polygon([(margin, margin), (size-margin, margin),(size//2, size//2)], fill=(52, 152, 219))
        draw.polygon([(margin, size-margin), (size-margin, size-margin),(size//2, size//2)], fill=(41, 128, 185))
        
        return image

    def show_window(self):
        """Show the application window from the system tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_tracking_from_tray(self):
        """Toggle tracking from the system tray"""
        if not self.tracking_active:
            self.start_tracking()
            self.show_notification("Digital Wellness", "Tracking started")
        else:
            self.stop_tracking()
            self.show_notification("Digital Wellness", "Tracking stopped")

    def exit_app(self):
        """Exit the application from the system tray"""
        if self.tracking_active:
            self.stop_tracking()
        self.closing = True
        if self.ui_timer is not None:
            self.root.after_cancel(self.ui_timer)
        self.tray_icon.stop()
        self.root.destroy()

    def toggle_tracking(self):
        if not self.tracking_active:
            self.start_tracking()
        else:
            self.stop_tracking()

    def start_tracking(self):
        if self.tracking_thread and self.tracking_thread.is_alive():
            return  # Already tracking
            
        self.tracker.stop_requested = False
        self.tracker.stop_event.clear()
        self.tracking_active = True
        self.start_stop_button.config(text="Pause Tracking")
        self.status_bar.config(text="Tracking active...")
        
        self.tracking_thread = threading.Thread(target=self.tracker.track)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.last_chart_refresh = 0

    def stop_tracking(self):
        if self.tracking_active:
            self.tracking_active = False
            self.start_stop_button.config(text="Start Tracking")
            self.status_bar.config(text="Tracking stopped")
            self.tracker.stop_tracking()
            self.last_chart_refresh = 0

    def update_ui(self):
        """One main-thread timer owns all Overview widget and chart updates."""
        for _ in range(20):
            try:
                action = self.ui_actions.get_nowait()
            except queue.Empty:
                break
            action()
            if self.closing:
                return
        if hasattr(self, "insight_coverage"):
            self.refresh_insight_coverage()
        if hasattr(self, 'day_picker'):
            self.refresh_day_choices()
        usage = self.overview_usage()
        if self.tracking_active:
            self.tracking_badge.config(text="TRACKING ACTIVE")
            app = self.tracker.current_app
            self.current_app_label.config(
                text=self.short_app_name(app, 42) if app else "Waiting for an active application…")
            title = self.tracker.current_window or "Foreground application monitoring is running."
            self.current_window_label.config(text=title[:65] + ("…" if len(title) > 65 else ""))
        else:
            self.tracking_badge.config(text="TRACKING PAUSED" if usage else "READY TO BEGIN")
            self.current_app_label.config(text="A moment to step away." if usage
                                          else "Make a little room for yourself.")
            self.current_window_label.config(text="Your daily totals stay saved after you quit." if usage
                                              else "Start tracking to see your application usage.")
        self.update_progress_bars(usage)
        now = time.monotonic()
        if now - self.last_chart_refresh >= 5:
            self.update_stats_display(usage)
            self.last_chart_refresh = now
        self.ui_timer = self.root.after(1000, self.update_ui)

    def update_progress_bars(self, usage=None):
        usage = self.overview_usage() if usage is None else usage
        total = sum(usage.values())
        self.summary_values[0].config(text=self.format_time(total))
        most_used = next(iter(usage), None)
        self.summary_values[1].config(
            text=self.short_app_name(most_used, 18) if most_used else "—")
        self.summary_details[1].config(
            text=f"{self.format_time(usage[most_used])} · {usage[most_used] / total:.0%} of period"
            if most_used else "Your most-used app will appear here")
        nearing = sum(1 for app, seconds in usage.items()
                      if self.tracker.app_limits.get(app, 0) > 0
                      and seconds >= self.tracker.warning_times.get(
                          app, self.tracker.app_limits[app] * .8))
        self.summary_values[2].config(text=f"{nearing} app{'s' if nearing != 1 else ''}")
        entries = list(usage.items())[:5]
        if entries:
            self.empty_usage.pack_forget()
        else:
            self.empty_usage.pack(anchor="w", pady=25)
        for index, row in enumerate(self.overview_rows):
            if index >= len(entries):
                row["frame"].pack_forget()
                continue
            app, seconds = entries[index]
            row["frame"].pack(fill="x", pady=(0, 6))
            row["name"].config(text=self.short_app_name(app))
            row["duration"].config(text=self.format_time(seconds))
            limit = self.tracker.app_limits.get(app, 0)
            if limit > 0:
                fraction = seconds / limit
                warning = self.tracker.warning_times.get(app, limit * .8)
                row["color"] = "danger" if seconds >= limit else "warning" if seconds >= warning else "accent"
                detail = f"{fraction:.0%} of {self.format_time(limit)} limit"
                if seconds >= limit:
                    detail += " · Limit reached"
            else:
                fraction = seconds / total if total else 0
                row["color"] = "accent"
                detail = f"{fraction:.0%} of period · No limit"
            row["fraction"] = min(1, max(0, fraction))
            row["detail"].config(text=detail)
            self.paint_usage_bar(row)

    def update_stats_display(self, usage=None):
        usage = self.overview_usage() if usage is None else usage
        self.ax.clear()
        self.figure.set_facecolor(self.palette["card"])
        self.ax.set_facecolor(self.palette["card"])
        entries = list(usage.items())[:5]
        for spine in self.ax.spines.values():
            spine.set_visible(False)
        if not entries:
            self.ax.set_axis_off()
            self.ax.text(.5, .5, "Your time, in perspective.\nStart tracking to build your chart.",
                         ha="center", va="center", transform=self.ax.transAxes,
                         color=self.palette["muted"], fontsize=10, linespacing=1.8)
            self.figure.subplots_adjust(left=.08, right=.95, top=.95, bottom=.12)
        else:
            self.ax.set_axis_on()
            values = [seconds / 60 for _, seconds in entries]
            positions = list(range(len(entries)))
            self.ax.barh(positions, values, color=self.palette["accent"], height=.48)
            self.ax.set_yticks(positions)
            self.ax.set_yticklabels([self.short_app_name(app, 16) for app, _ in entries], fontsize=9)
            self.ax.invert_yaxis()
            self.ax.set_xlim(0, max(values) * 1.3)
            self.ax.tick_params(axis="both", colors=self.palette["muted"], length=0, labelsize=8)
            self.ax.xaxis.set_major_locator(plt.MaxNLocator(4))
            self.ax.xaxis.grid(True, color=self.palette["track"], linewidth=.6)
            self.ax.set_axisbelow(True)
            for index, value in enumerate(values):
                self.ax.text(value + max(values) * .025, index, f"{value:.1f}",
                             va="center", color=self.palette["ink"], fontsize=9)
            self.figure.subplots_adjust(left=.29, right=.96, top=.94, bottom=.13)
        self.canvas.draw_idle()

    def update_limits_display(self):
        for item in self.limits_tree.get_children():
            self.limits_tree.delete(item)
        
        for app, limit in sorted(self.tracker.app_limits.items()):
            warning = self.tracker.warning_times.get(app, limit * 0.8)
            self.limits_tree.insert("", "end", iid=app, values=(app, self.format_time(limit), self.format_time(warning)))
        self.limits_empty.configure(text="" if self.tracker.app_limits else "No limits yet. Add your first app using the form.")

    def add_app_limit(self):
        self.editing_limit = None
        self.limits_tree.selection_remove(self.limits_tree.selection())
        self.remove_limit_button.configure(state='disabled')
        self.save_limit_button.configure(text='Save limit')
        self.limit_app_entry.configure(state="normal")
        self.limit_app_entry.configure(values=self.app_choices)
        self.limit_app_var.set("")
        self.limit_minutes_var.set("60")
        self.warning_minutes_var.set("48")
        self.limit_editor_title.configure(text="Add an application")
        self.limit_form_message.configure(text="")
        self.limit_app_entry.focus_set()

    def edit_app_limit(self, event=None):
        selected = self.limits_tree.selection()
        self.remove_limit_button.configure(state='normal' if selected else 'disabled')
        if not selected:
            return
        app = self.limits_tree.item(selected[0], "values")[0]
        if app not in self.tracker.app_limits:
            return
        changed = self.editing_limit != app
        if not changed and event is not None:
            return
        self.editing_limit = app
        self.limit_app_var.set(app)
        self.limit_app_entry.configure(state="disabled")
        self.limit_minutes_var.set(f"{self.tracker.app_limits[app] / 60:.10g}")
        self.warning_minutes_var.set(f"{self.tracker.warning_times.get(app, self.tracker.app_limits[app] * .8) / 60:.10g}")
        self.limit_editor_title.configure(text="Edit daily limit")
        self.save_limit_button.configure(text='Save changes')
        if changed:
            self.limit_form_message.configure(text="")

    def remove_app_limit(self):
        selected = self.limits_tree.selection()
        if not selected:
            messagebox.showwarning("Remove Limit", "Please select an app to remove")
            return
            
        app_name = self.limits_tree.item(selected[0], "values")[0]
        
        if messagebox.askyesno("Remove Limit", f"Remove limit for {app_name}?"):
            previous_limits = self.tracker.app_limits.copy()
            previous_warnings = self.tracker.warning_times.copy()
            if app_name in self.tracker.app_limits:
                del self.tracker.app_limits[app_name]
            if app_name in self.tracker.warning_times:
                del self.tracker.warning_times[app_name]
            try:
                self.tracker.save_config()
            except OSError as error:
                self.tracker.app_limits = previous_limits
                self.tracker.warning_times = previous_warnings
                self.limit_form_message.configure(text=f'Could not remove limit: {error}')
                return
            self.update_limits_display()
            self.add_app_limit()
            self.limit_form_message.configure(text=f'Removed limit for {app_name}.')

    def detect_active_apps(self):
        apps = set()
        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    apps.add(psutil.Process(pid).name().lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        try:
            win32gui.EnumWindows(collect, None)
        except Exception as error:
            self.limit_form_message.configure(text=f'Could not refresh apps: {error}')
            return
        self.app_choices = sorted(apps | set(self.tracker.app_limits))
        self.limit_app_entry.configure(values=self.app_choices)
        self.limit_form_message.configure(text=(
            'App list refreshed. Choose New limit to add another app.' if self.editing_limit else
            'App list refreshed. Type to filter or use the dropdown.' if self.app_choices else
            'No apps found. You can type a process name.'))

    def schedule_auto_analysis(self):
        now = datetime.now()
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        delay = (target - now).total_seconds()
        self.root.after(int(delay * 1000), self.analyze_usage)

    def analyze_usage(self):
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')

            df = pd.DataFrame(self.tracker.daily_store.rows(), columns=['date', 'app', 'duration'])
            if df.empty:
                messagebox.showinfo("Smart Insights", "No usage data available.")
                return

            pivot = df.pivot_table(index='date', columns='app', values='duration', aggfunc='sum').fillna(0)

            if len(pivot) < 3:
                messagebox.showinfo("Smart Insights", "Not enough days of data to analyze (need at least 3 days).")
                return

            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            pivot_scaled = pd.DataFrame(
                scaler.fit_transform(pivot),
                index=pivot.index,
                columns=pivot.columns
            )

            from sklearn.cluster import KMeans
            import numpy as np
            from sklearn.metrics import silhouette_score

            max_clusters = min(5, len(pivot) - 1)
            if max_clusters < 2:
                max_clusters = 2

            best_score = -1
            best_n_clusters = 3

            for n_clusters in range(2, max_clusters + 1):
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(pivot_scaled)

                if len(np.unique(cluster_labels)) > 1:
                    score = silhouette_score(pivot_scaled, cluster_labels)
                    if score > best_score:
                        best_score = score
                        best_n_clusters = n_clusters

            model = KMeans(n_clusters=best_n_clusters, random_state=42, n_init=10)
            pivot['cluster'] = model.fit_predict(pivot_scaled)

            if today_str not in pivot.index:
                messagebox.showinfo("Smart Insights", "No usage data for today.")
                return

            today_cluster = pivot.loc[today_str]['cluster']
            cluster_totals = pivot.groupby('cluster').sum().sum(axis=1)
            sorted_clusters = cluster_totals.sort_values()

            if len(sorted_clusters) >= 3:
                cluster_labels = {
                    sorted_clusters.index[0]: "Low Usage",
                    sorted_clusters.index[-1]: "High Usage"
                }
                for i in range(1, len(sorted_clusters) - 1):
                    cluster_labels[sorted_clusters.index[i]] = f"Moderate Usage {i}"
            else:
                cluster_labels = {
                    sorted_clusters.index[0]: "Lower Usage",
                    sorted_clusters.index[-1]: "Higher Usage"
                }

            today_label = cluster_labels[today_cluster]
            user_trend = self._calculate_usage_trend(pivot, today_str)

            recommendation = f"Today: {today_label}\n"
            recommendation += f"Trend: {user_trend}\n\n"

            today_data = df[df['date'] == today_str]
            top_apps = today_data.groupby('app')['duration'].sum().sort_values(ascending=False).head(5)

            total_usage = today_data['duration'].sum()
            recommendation += f"Total screen time: {self.format_time(total_usage)}\n\n"
            recommendation += "Top apps today:\n"

            for app, duration in top_apps.items():
                percentage = (duration / total_usage) * 100 if total_usage > 0 else 0
                recommendation += f"• {app}: {self.format_time(duration)} ({percentage:.1f}%)\n"

            self.recommendation_text.config(state=tk.NORMAL)
            self.recommendation_text.delete(1.0, tk.END)
            self.recommendation_text.insert(tk.END, recommendation)
            self.recommendation_text.config(state=tk.DISABLED)

            if self.voice_alerts_var.get():
                alert_message = f"Today is a {today_label} day. {user_trend}. Check your insights."
                self.tracker.voice_alert(alert_message)

            # ✅ Set flag after successful generation
            self.insights_generated_for = today_str

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("Smart Insights", f"Failed to analyze usage: {str(e)}")
            with open('error_log.txt', 'a') as f:
                f.write(f"{datetime.now()}: {error_details}\n")

                
    def _calculate_usage_trend(self, pivot, today_str):
        """Calculate usage trend compared to previous days."""
        try:
            dates = sorted(pivot.index)
            today_idx = dates.index(today_str)
            
            if today_idx == 0:  # First day of data
                return "First day of tracking"
                
            today_total = pivot.loc[today_str].drop('cluster').sum()
            
            lookback_days = min(3, today_idx)
            prev_days = dates[today_idx-lookback_days:today_idx]
            prev_avg = pivot.loc[prev_days].drop('cluster', axis=1).sum(axis=1).mean()
            
            if prev_avg > 0:
                change_pct = ((today_total - prev_avg) / prev_avg) * 100
                
                if change_pct > 20:
                    return f"↑ {change_pct:.1f}% higher than your average"
                elif change_pct < -20:
                    return f"↓ {change_pct:.1f}% lower than your average"
                else:
                    return "Similar to your recent usage"
            else:
                return "No previous data for comparison"
                
        except Exception as e:
            return "Unable to calculate trend"


    def format_time(self, seconds):
        """Format seconds into HH:MM:SS"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def show_notification(self, title, message):
        """Show a system notification"""
        if hasattr(self, 'tray_notifications_var') and self.tray_notifications_var.get():
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Digital Wellness",
                    timeout=5
                )
            except Exception as e:
                print(f"Failed to show notification: {e}")
    
    def on_closing(self):
        """Handle window close event"""
        if hasattr(self, 'minimize_to_tray_var') and self.minimize_to_tray_var.get():
            self.root.withdraw()
            self.show_notification("Digital Wellness", "App minimized to system tray")
        else:
            if self.tracking_active:
                if messagebox.askyesno("Quit", "Tracking is active. Stop tracking and quit?"):
                    self.stop_tracking()
                    self.exit_app()
            else:
                self.exit_app()


class ScreenTimeTracker:
    def __init__(self, gui=None):
        self.gui = gui
        self.state_lock = threading.RLock()
        self.stop_event = threading.Event()
        self.daily_store = DailyUsageStore()
        self.started_monotonic = None
        self.app_limits = {}
        self.warning_times = {}
        self.warned_apps = {}
        self.session_data = defaultdict(lambda: {'time': 0, 'windows': defaultdict(float)})
        self.total_usage = defaultdict(float)
        
        try:
            self.engine = pyttsx3.init()
        except:
            print("Warning: Could not initialize text-to-speech engine")
            self.engine = None
            
        self.current_app = None
        self.current_window = None
        self.start_time = None
        self.week_start_date = datetime.now().date() - timedelta(days=datetime.now().weekday())
        self.load_config()
        self.stop_requested = False

        if not os.path.exists('logs'):
            os.makedirs('logs')

    def load_config(self):
        """Load configuration from file or create default"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.app_limits = config.get('app_limits', {})
                    self.warning_times = config.get('warning_times', {})
                    self.total_usage = defaultdict(float, config.get('total_usage', {}))
        except Exception as e:
            print(f"Error loading config: {e}")
            self.app_limits = {}
            self.warning_times = {}

    def save_config(self):
        """Save current configuration to file"""
        config = {
            'app_limits': self.app_limits,
            'warning_times': self.warning_times,
            'total_usage': dict(self.total_usage)
        }
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)

    def get_active_window_info(self):
        """Get the current active window title and process name"""
        try:
            window = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(window)
            _, pid = win32process.GetWindowThreadProcessId(window)
            process = psutil.Process(pid)
            return title, process.name().lower()
        except Exception as e:
            print(f"Error getting window info: {e}")
            return None, None
        
    def voice_alert(self, message):
        """Issue a voice alert with proper COM initialization"""
        if self.gui and not hasattr(self.gui, 'voice_alerts_var') or not self.gui.voice_alerts_var.get():
            return  # Voice alerts disabled
            
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass  # For non-Windows systems

        try:
            if not hasattr(self, 'engine') or not self.engine:
                self.engine = pyttsx3.init()
                
            self.engine.stop()
            self.engine.say(message)
            self.engine.runAndWait()
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Voice alert failed: {e}")
            try:
                self.engine = pyttsx3.init()
            except:
                print("Failed to reinitialize voice engine")
                
        finally:
            try:
                pythoncom.CoUninitialize()
            except:
                pass

    def enforce_limit(self, app_name):
        """Forcefully close the application"""
        if self.gui and hasattr(self.gui, 'auto_shutdown_var') and not self.gui.auto_shutdown_var.get():
            return False  # Auto shutdown disabled
            
        for proc in psutil.process_iter(['name', 'pid']):
            if proc.info['name'].lower() == app_name:
                try:
                    # Send termination signal to the process
                    process = psutil.Process(proc.info['pid'])
                    process.terminate()
                    
                    # Show notification
                    if self.gui:
                        self.gui.show_notification(
                            "Time Limit Reached", 
                            f"{app_name} has been closed because you reached your time limit."
                        )
                    
                    # Voice alert
                    self.voice_alert(f"Time limit reached for {app_name}. Application has been closed.")
                    return True
                    
                except Exception as e:
                    print(f"Failed to terminate {app_name}: {e}")
                    
        return False

    def track(self):
        """Commit samples while running; stop and recording share the same lock."""
        failure = None
        try:
            while not self.stop_requested:
                window_title, app_name = self.get_active_window_info()
                with self.state_lock:
                    if self.stop_requested:
                        break
                    if self.current_app:
                        self.log_app_usage(self.current_app, self.current_window)
                    self.current_app = app_name
                    self.current_window = window_title
                    self.start_time = time.time() if app_name else None
                    self.started_monotonic = time.monotonic() if app_name else None
                    day = datetime.now().date().isoformat()
                    app_total = self.daily_store.usage(day).get(app_name, 0)
                if app_name and not self.stop_requested:
                    warning_time = self.warning_times.get(app_name)
                    warning_key = (day, app_name)
                    if warning_time and app_total >= warning_time and not self.warned_apps.get(warning_key):
                        self.warned_apps[warning_key] = True
                        remaining = max(0, int(self.app_limits.get(app_name, 0) - app_total))
                        self.voice_alert(f"Warning: You have {remaining} seconds left for {app_name}")
                    limit = self.app_limits.get(app_name, 0)
                    if limit > 0 and app_total >= limit:
                        self.enforce_limit(app_name)
                self.stop_event.wait(1)
        except Exception as error:
            failure = str(error)
        finally:
            with self.state_lock:
                try:
                    if self.current_app:
                        self.log_app_usage(self.current_app, self.current_window)
                    self.save_config()
                except Exception as error:
                    failure = str(error)
                finally:
                    self.current_app = None
                    self.current_window = None
                    self.start_time = None
                    self.started_monotonic = None
                    self.stop_requested = True
            if self.gui:
                if failure:
                    self.gui.ui_actions.put(lambda message=failure: messagebox.showerror(
                        "Tracking stopped", f"Could not save all usage: {message}"))
                self.gui.ui_actions.put(self.gui.tracking_finished)

    def log_app_usage(self, app_name, window_title):
        with self.state_lock:
            if self.start_time is None or self.started_monotonic is None:
                return
            now = time.monotonic()
            elapsed = max(0, now - self.started_monotonic)
            if elapsed <= 0:
                return
            # Advance the interval only after the durable write succeeds.
            self.daily_store.record(app_name, self.start_time, elapsed)
            self.session_data[app_name]["time"] += elapsed
            self.session_data[app_name]["windows"][window_title] += elapsed
            self.total_usage[app_name] += elapsed
            self.start_time = time.time()
            self.started_monotonic = now

    def stop_tracking(self):
        self.stop_event.set()
        with self.state_lock:
            self.stop_requested = True
            if self.current_app:
                self.log_app_usage(self.current_app, self.current_window)
            self.current_app = None
            self.current_window = None
            self.start_time = None
            self.started_monotonic = None
            self.save_config()


def main():
    # The tray can keep an instance alive after its window is closed. Prevent
    # a second process from overwriting the first process's daily snapshots.
    import msvcrt
    root = tk.Tk()
    root.withdraw()
    application_path = sys.executable if getattr(sys, 'frozen', False) else __file__
    data_dir = Path(application_path).resolve().parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    with open(data_dir / 'tracker.lock', 'a+b') as instance:
        instance.seek(0, os.SEEK_END)
        if instance.tell() == 0:
            instance.write(b'0')
            instance.flush()
        instance.seek(0)
        try:
            msvcrt.locking(instance.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            messagebox.showinfo('Already running',
                                'Digital Wellbeing Tracker is already running. Open it from the system tray.')
            root.destroy()
            return
        try:
            app = DigitalWellnessApp(root)
            root.deiconify()
            root.mainloop()
        except Exception as error:
            messagebox.showerror('Unable to start tracker', str(error))
            root.destroy()
        finally:
            instance.seek(0)
            msvcrt.locking(instance.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    main()


