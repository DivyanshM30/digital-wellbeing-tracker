import os
import time
import json
from datetime import datetime, timedelta
import psutil
import win32gui
import win32process
import pyttsx3
from collections import defaultdict
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import sys
import pystray
from PIL import Image, ImageDraw
from plyer import notification
import sv_ttk   
import pandas as pd
from sklearn.cluster import KMeans

class DigitalWellnessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Digital Wellness Tracker")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.dark_mode = tk.BooleanVar(value=False)
        
        self.tracker = ScreenTimeTracker(self)
        self.insights_generated_for = None
        self.create_widgets()
        
        self.setup_system_tray()

        self.tracking_active = False
        self.tracking_thread = None
        
        self.toggle_theme()
        
        self.schedule_auto_analysis()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        
        self.current_app_frame = ttk.LabelFrame(self.dashboard_frame, text="Currently Tracking")
        self.current_app_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_app_label = ttk.Label(self.current_app_frame, text="Not tracking any app")
        self.current_app_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.start_stop_button = ttk.Button(self.current_app_frame, text="Start Tracking", command=self.toggle_tracking)
        self.start_stop_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.progress_frame = ttk.LabelFrame(self.dashboard_frame, text="Today's Usage")
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.progress_bars = {}
        
        self.stats_frame = ttk.Frame(self.dashboard_frame)
        self.stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.figure = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, self.stats_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.limits_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.limits_frame, text="App Limits")
        
        self.limits_tree = ttk.Treeview(self.limits_frame, columns=("app", "limit", "warning"), show="headings")
        self.limits_tree.heading("app", text="Application")
        self.limits_tree.heading("limit", text="Limit (seconds)")
        self.limits_tree.heading("warning", text="Warning (seconds)")
        self.limits_tree.column("app", width=200)
        self.limits_tree.column("limit", width=100)
        self.limits_tree.column("warning", width=100)
        self.limits_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.limits_button_frame = ttk.Frame(self.limits_frame)
        self.limits_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(self.limits_button_frame, text="Add Limit",command=self.add_app_limit).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.limits_button_frame, text="Edit Limit",command=self.edit_app_limit).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.limits_button_frame, text="Remove Limit",command=self.remove_app_limit).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.limits_button_frame, text="Detect Apps",command=self.detect_active_apps).pack(side=tk.LEFT, padx=5)
        
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        self.smart_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.smart_frame, text="Smart Insights")
        
        self.analyze_button = ttk.Button(self.smart_frame, text="Analyze My Usage", command=self.analyze_usage)
        self.analyze_button.pack(pady=20)
        
        self.recommendation_text = tk.Text(self.smart_frame, height=15, wrap=tk.WORD)
        self.recommendation_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.recommendation_text.config(state=tk.DISABLED)
        
        self.voice_alerts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.settings_frame, text="Voice Alerts", 
                        variable=self.voice_alerts_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.auto_shutdown_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.settings_frame, text="Auto Shutdown Apps at Limit", 
                        variable=self.auto_shutdown_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.tray_notifications_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.settings_frame, text="System Tray Notifications", 
                        variable=self.tray_notifications_var).pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Checkbutton(self.settings_frame, text="Dark Mode", 
                        variable=self.dark_mode, 
                        command=self.toggle_theme).pack(anchor=tk.W, padx=10, pady=5)
        
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.settings_frame, text="Minimize to System Tray", 
                        variable=self.minimize_to_tray_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.load_app_settings()
        self.update_limits_display()
        self.update_stats_display()

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

    def toggle_theme(self):
        """Toggle between light and dark mode"""
        if self.dark_mode.get():
            sv_ttk.set_theme("dark")
            self.figure.set_facecolor('#2d2d2d')
            self.ax.set_facecolor('#2d2d2d')
            self.ax.tick_params(colors='white')
            self.ax.xaxis.label.set_color('white')
            self.ax.yaxis.label.set_color('white')
            self.ax.title.set_color('white')
        else:
            sv_ttk.set_theme("light")
            self.figure.set_facecolor('#f0f0f0')
            self.ax.set_facecolor('#f0f0f0')
            self.ax.tick_params(colors='black')
            self.ax.xaxis.label.set_color('black')
            self.ax.yaxis.label.set_color('black')
            self.ax.title.set_color('black')
        
        self.canvas.draw()
        
        self.save_app_settings()

    def setup_system_tray(self):
        """Setup the system tray icon and menu"""
        icon_image = self.create_tray_icon()
        
        menu_items = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Start/Stop Tracking', self.toggle_tracking_from_tray),
            pystray.MenuItem('Exit', self.exit_app)
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
        self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)

    def toggle_tracking(self):
        if not self.tracking_active:
            self.start_tracking()
        else:
            self.stop_tracking()

    def start_tracking(self):
        if self.tracking_thread and self.tracking_thread.is_alive():
            return  # Already tracking
            
        self.tracking_active = True
        self.start_stop_button.config(text="Stop Tracking")
        self.status_bar.config(text="Tracking active...")
        
        self.tracking_thread = threading.Thread(target=self.tracker.track)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        
        self.root.after(1000, self.update_ui)

    def stop_tracking(self):
        if self.tracking_active:
            self.tracking_active = False
            self.start_stop_button.config(text="Start Tracking")
            self.status_bar.config(text="Tracking stopped")
            self.tracker.stop_tracking()

    def update_ui(self):
        if not self.tracking_active:
            return
            
        if self.tracker.current_app:
            app_name = self.tracker.current_app
            window_title = self.tracker.current_window
            truncated_title = window_title[:40] + "..." if len(window_title) > 40 else window_title
            
            current_time = time.time()
            elapsed = current_time - self.tracker.start_time if self.tracker.start_time else 0
            total_time = self.tracker.session_data[app_name]['time'] + elapsed
            
            limit = self.tracker.app_limits.get(app_name, 0)
            if limit > 0:
                percent = min(100, (total_time / limit) * 100)
                status_text = f"Currently using: {app_name} - {truncated_title} - {self.format_time(total_time)} / {self.format_time(limit)} ({percent:.0f}%)"
            else:
                status_text = f"Currently using: {app_name} - {truncated_title} - {self.format_time(total_time)}"
                
            self.current_app_label.config(text=status_text)
        else:
            self.current_app_label.config(text="Not tracking any app")
        
        self.update_progress_bars()
        
        self.root.after(1000, self.update_ui)

    def update_progress_bars(self):
        for widget in self.progress_frame.winfo_children():
            widget.destroy()
        
        app_usage = []
        for app, data in self.tracker.session_data.items():
            if app == self.tracker.current_app and self.tracker.start_time:
                elapsed = time.time() - self.tracker.start_time
                usage = data['time'] + elapsed
            else:
                usage = data['time']
            app_usage.append((app, usage))
        
        for app, usage in self.tracker.total_usage.items():
            if app not in [a[0] for a in app_usage]:
                app_usage.append((app, 0))  # Only count session time in progress bars
        
        app_usage.sort(key=lambda x: x[1], reverse=True)
        
        for i, (app, usage) in enumerate(app_usage[:5]):
            app_frame = ttk.Frame(self.progress_frame)
            app_frame.pack(fill=tk.X, padx=5, pady=2)
            
            limit = self.tracker.app_limits.get(app, 0)
            
            if limit > 0:
                label_text = f"{app}: {self.format_time(usage)} / {self.format_time(limit)}"
                progress = min(100, (usage / limit) * 100)
            else:
                label_text = f"{app}: {self.format_time(usage)}"
                progress = min(100, usage / 3600 * 100)  # As percentage of 1 hour if no limit
            
            ttk.Label(app_frame, text=label_text, width=30, anchor=tk.W).pack(side=tk.LEFT)
            
            style_name = f"color{i}.Horizontal.TProgressbar"
            ttk.Style().configure(style_name, background=self.get_progress_color(progress))
            
            progress_bar = ttk.Progressbar(app_frame, style=style_name, length=300, mode="determinate")
            progress_bar["value"] = progress
            progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def get_progress_color(self, percentage):
        if percentage > 80:
            return "#FF5733"  # Red
        elif percentage > 60:
            return "#FFC300"  # Yellow
        else:
            return "#4CAF50"  # Green

    def update_stats_display(self):
        self.ax.clear()
        
        apps = []
        times = []
        
        usage_data = defaultdict(float)
        for app, data in self.tracker.session_data.items():
            if app == self.tracker.current_app and self.tracker.start_time:
                elapsed = time.time() - self.tracker.start_time
                usage_data[app] = data['time'] + elapsed
            else:
                usage_data[app] = data['time']
        
        for app, usage in self.tracker.total_usage.items():
            if app not in usage_data:
                usage_data[app] = 0  # Only count session time in chart
        
        for app, time_spent in sorted(usage_data.items(), key=lambda x: x[1], reverse=True)[:8]:
            apps.append(app)
            times.append(time_spent / 60)  # Convert to minutes for readability
        
        if apps:
            bars = self.ax.bar(apps, times, color='skyblue')
            
            if self.dark_mode.get():
                self.ax.set_facecolor('#2d2d2d')
                self.ax.tick_params(colors='white')
                self.ax.xaxis.label.set_color('white')
                self.ax.yaxis.label.set_color('white')
                self.ax.title.set_color('white')
            else:
                self.ax.set_facecolor('#f0f0f0')
                self.ax.tick_params(colors='black')  
                self.ax.xaxis.label.set_color('black')
                self.ax.yaxis.label.set_color('black')
                self.ax.title.set_color('black')
            
            self.ax.set_title('Application Usage')
            self.ax.set_xlabel('Applications')
            self.ax.set_ylabel('Time (minutes)')

            x_positions = range(len(apps))  # get positions for each bar
            self.ax.set_xticks(x_positions)  # explicitly set ticks
            self.ax.set_xticklabels(apps, rotation=45, ha='right')  # now set labels
            
            for bar in bars:
                height = bar.get_height()
                self.ax.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                        f'{height:.1f}', ha='center', va='bottom',
                        color='white' if self.dark_mode.get() else 'black')
            self.figure.set_size_inches(12, 6)
            self.figure.tight_layout()
            
        self.canvas.draw()

    def update_limits_display(self):
        for item in self.limits_tree.get_children():
            self.limits_tree.delete(item)
        
        for app, limit in sorted(self.tracker.app_limits.items()):
            warning = self.tracker.warning_times.get(app, limit * 0.8)
            self.limits_tree.insert("", "end", values=(app, limit, warning))

    def add_app_limit(self):
        app_name = simpledialog.askstring("Add App Limit", "Application name:")
        if not app_name:
            return
            
        limit = simpledialog.askinteger("Add App Limit", f"Time limit for {app_name} (seconds):")
        if not limit:
            return
            
        warning = simpledialog.askinteger("Add App Limit", f"Warning time for {app_name} (seconds):", 
                                         initialvalue=int(limit * 0.8))
        if warning is None:
            warning = int(limit * 0.8)
        
        self.tracker.app_limits[app_name] = limit
        self.tracker.warning_times[app_name] = warning
        self.tracker.save_config()
        
        self.update_limits_display()

    def edit_app_limit(self):
        selected = self.limits_tree.selection()
        if not selected:
            messagebox.showwarning("Edit Limit", "Please select an app to edit")
            return
            
        app_name = self.limits_tree.item(selected[0], "values")[0]
        current_limit = self.tracker.app_limits.get(app_name, 0)
        current_warning = self.tracker.warning_times.get(app_name, current_limit * 0.8)
        
        limit = simpledialog.askinteger("Edit App Limit", f"Time limit for {app_name} (seconds):",initialvalue=current_limit)
        if not limit:
            return
            
        warning = simpledialog.askinteger("Edit App Limit", f"Warning time for {app_name} (seconds):",initialvalue=current_warning)
        if warning is None:
            warning = int(limit * 0.8)
        
        self.tracker.app_limits[app_name] = limit
        self.tracker.warning_times[app_name] = warning
        self.tracker.save_config()
        
        self.update_limits_display()

    def remove_app_limit(self):
        selected = self.limits_tree.selection()
        if not selected:
            messagebox.showwarning("Remove Limit", "Please select an app to remove")
            return
            
        app_name = self.limits_tree.item(selected[0], "values")[0]
        
        if messagebox.askyesno("Remove Limit", f"Remove limit for {app_name}?"):
            # Update tracker config
            if app_name in self.tracker.app_limits:
                del self.tracker.app_limits[app_name]
            if app_name in self.tracker.warning_times:
                del self.tracker.warning_times[app_name]
            self.tracker.save_config()
            
            self.update_limits_display()

    def detect_active_apps(self):
        foreground_apps = set()
        
        def window_enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    foreground_apps.add(process.name().lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        win32gui.EnumWindows(window_enum_callback, None)
        
        if not foreground_apps:
            messagebox.showinfo("Detect Apps", "No foreground applications detected")
            return
        
        select_dialog = tk.Toplevel(self.root)
        select_dialog.title("Select Applications")
        select_dialog.geometry("400x400")
        select_dialog.transient(self.root)
        select_dialog.grab_set()
        
        tk.Label(select_dialog, text="Select applications to set limits:").pack(padx=10, pady=5)
        
        app_vars = {}
        for app in sorted(foreground_apps):
            var = tk.BooleanVar(value=app in self.tracker.app_limits)
            app_vars[app] = var
            tk.Checkbutton(select_dialog, text=app, variable=var).pack(anchor=tk.W, padx=20, pady=2)
        
        def on_confirm():
            for app, var in app_vars.items():
                if var.get() and app not in self.tracker.app_limits:
                    limit = simpledialog.askinteger("Add App Limit", f"Time limit for {app} (seconds):", parent=select_dialog)
                    if limit:
                        self.tracker.app_limits[app] = limit
                        self.tracker.warning_times[app] = int(limit * 0.8)
            
            self.tracker.save_config()
            self.update_limits_display()
            select_dialog.destroy()
        
        tk.Button(select_dialog, text="Confirm", command=on_confirm).pack(pady=10)

    def schedule_auto_analysis(self):
        now = datetime.now()
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        delay = (target - now).total_seconds()
        self.root.after(int(delay * 1000), self.analyze_usage)

    def analyze_usage(self):
        try:
            self.log_daily_usage()

            today_str = datetime.now().strftime('%Y-%m-%d')

            # Prevent reprocessing for the same date
            if hasattr(self, 'insights_generated_for') and self.insights_generated_for == today_str:
                messagebox.showinfo("Smart Insights", "Insights already generated for today.")
                return

            if not os.path.exists('usage_log.csv'):
                messagebox.showinfo("Smart Insights", "No usage data found.")
                return

            df = pd.read_csv('usage_log.csv')
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

            total_usage = top_apps.sum()
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


    def log_daily_usage(self):
        today = datetime.now().strftime('%Y-%m-%d')
        usage_data = defaultdict(float)

        for app, data in self.tracker.session_data.items():
            if app == self.tracker.current_app and self.tracker.start_time:
                elapsed = time.time() - self.tracker.start_time
                usage_data[app] = data['time'] + elapsed
            else:
                usage_data[app] = data['time']

        if not usage_data:
            return

        if not os.path.exists('usage_log.csv'):
            with open('usage_log.csv', 'w', encoding='utf-8') as f:
                f.write("date,app,duration\n")

        with open('usage_log.csv', 'a', encoding='utf-8') as f:
            for app, duration in usage_data.items():
                app_clean = app.replace('\u200b', '')
                f.write(f"{today},{app_clean},{duration}\n")


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
        """Start tracking screen time"""
        self.stop_requested = False
        
        while not self.stop_requested:
            window_title, app_name = self.get_active_window_info()
            
            if not app_name:
                time.sleep(1)
                continue
                
            if app_name != self.current_app:
                if self.current_app:
                    self.log_app_usage(self.current_app, self.current_window)
                    
                self.current_app = app_name
                self.current_window = window_title
                self.start_time = time.time()
                
                self.warned_apps[app_name] = False
                
                if self.gui:
                    self.gui.update_stats_display()
                    
            else:
                elapsed = time.time() - self.start_time
                app_total = self.session_data[app_name]['time'] + elapsed
                
                warning_time = self.warning_times.get(app_name)
                if warning_time and app_total >= warning_time and not self.warned_apps.get(app_name, False):
                    self.warned_apps[app_name] = True
                    
                    limit = self.app_limits.get(app_name, 0)
                    remaining = int(limit - app_total)
                    
                    warning_msg = f"Warning: You have {remaining} seconds left for {app_name}"
                    
                    self.voice_alert(warning_msg)
                    
                    if self.gui:
                        self.gui.show_notification("Time Warning", warning_msg)
                
                limit = self.app_limits.get(app_name, 0)
                if limit > 0 and app_total >= limit:
                    self.log_app_usage(app_name, window_title)
                    
                    self.enforce_limit(app_name)
                    
                    self.current_app = None
                    self.current_window = None
                    self.start_time = None
                    
            time.sleep(1)
        
        if self.current_app:
            self.log_app_usage(self.current_app, self.current_window)
            
        self.save_config()

    def log_app_usage(self, app_name, window_title):
        """Log app usage from current session"""
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        if elapsed < 1:  # Ignore very short sessions
            return
            
        self.session_data[app_name]['time'] += elapsed
        self.session_data[app_name]['windows'][window_title] += elapsed
        
        self.total_usage[app_name] += elapsed
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = f"logs/{today}.log"
        
        try:
            with open(log_file, 'a') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                f.write(f"{timestamp} | {app_name} | {window_title} | {elapsed:.2f}s\n")
        except Exception as e:
            print(f"Error writing to log: {e}")
        
        self.start_time = time.time()

    def stop_tracking(self):
        """Stop the tracking process"""
        self.stop_requested = True
        
        if self.current_app:
            self.log_app_usage(self.current_app, self.current_window)
            
        self.current_app = None
        self.current_window = None
        self.start_time = None
        
        self.save_config()


def main():
    root = tk.Tk()
    app = DigitalWellnessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


