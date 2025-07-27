# Digital Wellbeing Tracker

A desktop-based application designed to monitor screen time, track active app usage, and promote healthier digital habits through real-time alerts and insightful usage statistics.

## Features

- **Real-time Application Monitoring:** Uses `psutil` to track active applications and system activity continuously.
- **Voice Alerts:** Integrated `pyttsx3` to deliver non-intrusive voice reminders after excessive screen usage.
- **Usage Visualization:** Visualizes daily and weekly screen time data using `matplotlib` for easy-to-understand graphs.
- **Responsive UI:** Implements multithreading to ensure smooth user experience without UI freezes during background monitoring.
- **Usage Pattern Analysis:** Employs machine learning techniques to analyze user habits and provide personalized insights.

## Technologies Used

- Python 3.x
- psutil
- pywin32
- pyttsx3
- matplotlib
- pystray
- Pillow
- plyer
- sv_ttk
- pandas
- scikit-learn
- tkinter (usually pre-installed)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/digital-wellbeing-tracker.git

2. Navigate to the project directory:

   ```bash
   cd digital-wellbeing-tracker
    ```
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
    ```

4. (Optional) To create a standalone executable (.exe) file, install PyInstaller: [In order to run it as an application]

```bash
pip install pyinstaller
```

5. Build the executable:

```bash
pyinstaller --onefile main.py
```

6. After building, find the .exe file inside the dist folder. You can run this executable without needing Python installed.

7. Run the application (if running as a script):

```bash
python main.py
