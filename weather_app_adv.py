import requests
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from datetime import datetime, timedelta
import sqlite3
import urllib.parse
from PIL import Image, ImageTk, ImageSequence

# ========================================
# Global Defaults and Constants
# ========================================
BACKGROUND = "#121212"  
ICON_SIZE = (70, 70)

# ========================================
# AnimatedGIF Class for Handling Animated GIFs in Tkinter
# ========================================
class AnimatedGIF(tk.Label):
    def __init__(self, master, filename, delay=100, icon_size=ICON_SIZE, **kwargs):
        tk.Label.__init__(self, master, **kwargs)
        self.delay = delay
        self.icon_size = icon_size
        self.frames = []
        self.current_frame = 0
        self.load_frames(filename)
        if self.frames:
            self.animate()

    def load_frames(self, filename):
        try:
            im = Image.open(filename)

            for frame in ImageSequence.Iterator(im):
                frame = frame.copy().resize(self.icon_size,
                        Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
                photo = ImageTk.PhotoImage(frame)
                self.frames.append(photo)
        except Exception as e:
            print(f"Error loading frames from {filename}: {e}")

    def animate(self):
        if self.frames:
            self.config(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(self.delay, self.animate)

# ========================================
# Function to Determine the Appropriate Weather Icon Filename
# ========================================
def get_weather_icon_filename(condition, wind_speed=None):
    condition_lower = condition.lower()
    gif_path = "/Users/vrajamin/Desktop/weather_app_project_Adv/"
    if "clear" in condition_lower:
        icon_filename = "sun.gif"
    elif "thunder" in condition_lower or "storm" in condition_lower:
        icon_filename = "stormy.gif"
    elif "rain" in condition_lower:
        icon_filename = "rainy.gif"
    elif "snow" in condition_lower:
        icon_filename = "snow.gif"
    elif "overcast" in condition_lower:
        icon_filename = "cloudy.gif"
    elif wind_speed is not None and wind_speed >= 15:
        icon_filename = "windy.gif"
    else:
        icon_filename = "partialy cloudy.gif"
    return gif_path + icon_filename

# ========================================
# RoundedFrame Class for Creating Frames with Rounded Corners
# ========================================
class RoundedFrame(tk.Canvas):
    def __init__(self, parent, corner_radius=15, padding=5, bg_color="white", **kwargs):
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = BACKGROUND
        tk.Canvas.__init__(self, parent, bg=parent_bg, highlightthickness=0, **kwargs)
        self.corner_radius = corner_radius
        self.padding = padding
        self.bg_color = bg_color
        self.frame = tk.Frame(self, bg=self.bg_color)
        self.create_window((self.padding, self.padding), window=self.frame, anchor="nw")
        self.bind("<Configure>", self._draw_rounded_rect)

    def _draw_rounded_rect(self, event=None):
        self.delete("round_rect")
        width = self.winfo_width()
        height = self.winfo_height()
        r = self.corner_radius
        self.create_arc((0, 0, 2*r, 2*r), start=90, extent=90,
                        fill=self.bg_color, outline=self.bg_color, tags="round_rect")
        self.create_arc((width-2*r, 0, width, 2*r), start=0, extent=90,
                        fill=self.bg_color, outline=self.bg_color, tags="round_rect")
        self.create_arc((0, height-2*r, 2*r, height), start=180, extent=90,
                        fill=self.bg_color, outline=self.bg_color, tags="round_rect")
        self.create_arc((width-2*r, height-2*r, width, height), start=270, extent=90,
                        fill=self.bg_color, outline=self.bg_color, tags="round_rect")
        self.create_rectangle((r, 0, width-r, height), fill=self.bg_color,
                              outline=self.bg_color, tags="round_rect")
        self.create_rectangle((0, r, width, height-r), fill=self.bg_color,
                              outline=self.bg_color, tags="round_rect")

# ========================================
# Database Initialization and Setup
# ========================================
def init_db():
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS weather_requests")
    cursor.execute("""
        CREATE TABLE weather_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            date TEXT NOT NULL,
            temperature TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ========================================
# Color Theme Configuration
# ========================================
PRIMARY = "#B886FC"
PRIMARY_VARIANT = "#3700B3"
SECONDARY = "#030AC5"
SURFACE = "#ff4b33"
ERROR = "#CF6679"
TEXT_ON_PRIMARY = "#000000"
TEXT_ON_SURFACE = "#FFFFFF"

# ========================================
# API Keys for Weather Data Services
# ========================================
API_KEY = "ae53373282fddf6392a2ad05266c48a2"
VISUAL_CROSSING_API_KEY = "WKBS2CXMLNNWJF3TNHJ9TAZX4"

# ========================================================================
# Functions for Fetching Current, Forecast, and Historical Weather Data
# ========================================================================
def get_weather(api_key, location):
    """Fetch current weather and 5-day forecast using OpenWeatherMap API."""
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
    geo_params = {"q": location, "limit": 1, "appid": api_key}
    geo_response = requests.get(geo_url, params=geo_params)
    if geo_response.status_code != 200 or not geo_response.json():
        print(f"Geo API Response: {geo_response.status_code}, {geo_response.text}")
        return None, None
    geo_data = geo_response.json()[0]
    lat, lon = geo_data["lat"], geo_data["lon"]
    weather_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"}
    forecast_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "imperial"}
    weather_response = requests.get(weather_url, params=weather_params)
    forecast_response = requests.get(forecast_url, params=forecast_params)
    print(f"Weather API Response: {weather_response.status_code}, {weather_response.text}")
    if weather_response.status_code == 200 and forecast_response.status_code == 200:
        return weather_response.json(), forecast_response.json()
    else:
        return None, None

def get_historical_weather(location, start_date, end_date):
    """Fetch historical weather data using the Visual Crossing API."""
    location_encoded = urllib.parse.quote(location)
    url = (f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
           f"{location_encoded}/{start_date}/{end_date}?key={VISUAL_CROSSING_API_KEY}"
           f"&unitGroup=us&include=days&contentType=json")
    print(f"API Request URL: {url}")
    response = requests.get(url)
    print(f"API Response Status Code: {response.status_code}")
    print(f"API Response Text: {response.text}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Visual Crossing API Error: {response.status_code}, {response.text}")
        return None

def get_location():
    """Automatically detect user location based on IP."""
    api_key = "57963b8f9b3b55"
    try:
        response = requests.get(f"https://ipinfo.io/json?token={api_key}")
        response.raise_for_status()
        ip_info = response.json()
        print(f"IPInfo Response: {ip_info}")
        city = ip_info.get("city", "")
        country = ip_info.get("country", "")
        if not city or not country:
            print("Error: Unable to find city or country.")
            return None, None
        return city, country
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location: {e}")
        return None, None

# =============================================
# Function to Format User Input for Location
# =============================================
def format_location_input(location):
    """
    If the user input already contains commas, assume it is correctly formatted.
    Otherwise, split the input by whitespace and insert commas.
    """
    if location.lower() == "auto":
        return "auto"
    if "," in location:
        parts = [part.strip() for part in location.split(",") if part.strip()]
        return ", ".join(parts)
    else:
        parts = location.split()
        if len(parts) < 2:
            return None
        if len(parts) == 2:
            return f"{parts[0]}, {parts[1]}"
        if len(parts) > 2:
            city = " ".join(parts[:-2])
            state = parts[-2]
            country = parts[-1]
            return f"{city}, {state}, {country}"
    return None

# =============================================================
# CRUD Operations for Weather Request Records in the Database
# =============================================================
def create_record(location, date, temperature):
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO weather_requests (location, date, temperature)
        VALUES (?, ?, ?)
    """, (location, date, temperature))
    conn.commit()
    conn.close()

def read_records():
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weather_requests")
    records = cursor.fetchall()
    conn.close()
    return records

def update_record(record_id, temperature):
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE weather_requests
        SET temperature = ?
        WHERE id = ?
    """, (temperature, record_id))
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM weather_requests WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# ================================================
# Function to Show Information about the Program
# =================================================
def show_info():
    info_text = (
        "The Product Manager Accelerator Program is designed to support PM professionals through every stage of their careers. "
        "From students looking for entry-level jobs to Directors looking to take on a leadership role, our program has helped over hundreds "
        "of students fulfill their career aspirations.\n\n"
        "Our Product Manager Accelerator community are ambitious and committed. Through our program they have learnt, honed and developed new PM "
        "and leadership skills, giving them a strong foundation for their future endeavors."
    )
    messagebox.showinfo("Information", info_text)

# ==============================================
# Function to Display Weather Data in the GUI
# ==============================================
def display_weather_in_gui(weather_data, forecast_data=None, is_historical=False):
    for widget in output_frame.winfo_children():
        widget.destroy()

    if is_historical:
        notebook = ttk.Notebook(output_frame)
        notebook.pack(fill="both", expand=True)
        font_hist = ("Helvetica", 20)
        for day in weather_data.get('days', []):
            date = day.get('datetime', 'Unknown')
            tab = RoundedFrame(notebook, corner_radius=15, padding=5, bg_color=SURFACE)
            notebook.add(tab, text=date)
            tk.Label(tab.frame, text=f"Location: {weather_data.get('resolvedAddress', 'Unknown')}",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(pady=5, fill="x", expand=True)
            tk.Label(tab.frame, text=f"Date: {date}",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(fill="x", expand=True)
            tk.Label(tab.frame, text=f"Temperature: {day.get('temp', 'N/A')}°F",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(fill="x", expand=True)
            tk.Label(tab.frame, text=f"Weather: {day.get('conditions', 'N/A')}",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(fill="x", expand=True)
            tk.Label(tab.frame, text=f"Humidity: {day.get('humidity', 'N/A')}%",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(fill="x", expand=True)
            tk.Label(tab.frame, text=f"Wind: {day.get('windspeed', 'N/A')} mph",
                     font=font_hist, bg=SURFACE, fg=TEXT_ON_SURFACE,
                     anchor="center", justify="center").pack(fill="x", expand=True)
            icon_filename = get_weather_icon_filename(day.get('conditions', ''), day.get('windspeed'))
            animated_icon = AnimatedGIF(tab, filename=icon_filename, delay=100, bg=SURFACE)
            animated_icon.place(relx=1.0, rely=1.0, anchor="se")
    else:
        today_frame = RoundedFrame(output_frame, corner_radius=15, padding=5, bg_color=SURFACE)
        today_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        font_current = ("Helvetica", 16)
        tk.Label(today_frame.frame, text="Today's Weather",
                 font=("Helvetica", 18, "bold"), bg=SURFACE, fg=TEXT_ON_SURFACE).pack(pady=5)
        tk.Label(today_frame.frame, text=f"Location: {weather_data.get('name', 'Unknown')}",
                 font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
        tk.Label(today_frame.frame, text=f"Temperature: {weather_data['main'].get('temp', 'N/A')}°F",
                 font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
        tk.Label(today_frame.frame, text=f"Weather: {weather_data['weather'][0].get('description', 'N/A').title()}",
                 font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
        tk.Label(today_frame.frame, text=f"Humidity: {weather_data['main'].get('humidity', 'N/A')}%",
                 font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
        tk.Label(today_frame.frame, text=f"Wind: {weather_data['wind'].get('speed', 'N/A')} mph",
                 font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
        icon_filename = get_weather_icon_filename(weather_data['weather'][0].get('description', ''), weather_data['wind'].get('speed'))
        animated_icon = AnimatedGIF(today_frame, filename=icon_filename, delay=100, bg=SURFACE)
        animated_icon.place(relx=1.0, rely=1.0, anchor="se")
        # Group forecast data by day
        forecast_by_day = {}
        for forecast in forecast_data["list"]:
            date = datetime.strptime(forecast['dt_txt'], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            if date not in forecast_by_day:
                forecast_by_day[date] = []
            forecast_by_day[date].append(forecast)
        # Display forecast for the next 5 days
        for i, (date, forecasts) in enumerate(list(forecast_by_day.items())[1:6], start=1):
            forecast_frame = RoundedFrame(output_frame, corner_radius=15, padding=5, bg_color=SURFACE)
            forecast_frame.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)
            display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%a, %b %d")
            tk.Label(forecast_frame.frame, text=display_date,
                     font=("Helvetica", 18, "bold"), bg=SURFACE, fg=TEXT_ON_SURFACE).pack(pady=5)
            tk.Label(forecast_frame.frame, text=f"Temp: {forecasts[0]['main'].get('temp', 'N/A')}°F",
                     font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
            tk.Label(forecast_frame.frame, text=f"Weather: {forecasts[0]['weather'][0].get('description', 'N/A').title()}",
                     font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
            tk.Label(forecast_frame.frame, text=f"Humidity: {forecasts[0]['main'].get('humidity', 'N/A')}%",
                     font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
            tk.Label(forecast_frame.frame, text=f"Wind: {forecasts[0]['wind'].get('speed', 'N/A')} mph",
                     font=font_current, bg=SURFACE, fg=TEXT_ON_SURFACE).pack()
            wind_speed = forecasts[0]['wind'].get('speed')
            icon_filename = get_weather_icon_filename(forecasts[0]['weather'][0].get('description', ''), wind_speed)
            animated_icon = AnimatedGIF(forecast_frame, filename=icon_filename, delay=100, bg=SURFACE)
            animated_icon.place(relx=1.0, rely=1.0, anchor="se")

# ======================================================
# Function to Fetch Weather Data and Save to Database
# ======================================================
def fetch_weather():
    location = location_entry.get().strip()
    start_date = start_date_entry.get().strip()
    end_date = end_date_entry.get().strip()
    print(f"User Input: {location}, Start Date: {start_date}, End Date: {end_date}")

    if location.lower() == "auto":
        city, country = get_location()
        print(f"Auto-detected Location: {city}, {country}")
        if not city or not country:
            messagebox.showerror("Error", "Unable to determine your location.")
            return
        location = f"{city}, {country}"
        start_date = ""
        end_date = ""
    else:
        formatted_location = format_location_input(location)
        print(f"Formatted Location: {formatted_location}")
        if not formatted_location:
            messagebox.showerror("Error", "Invalid location format. Use 'City, Country' or 'City, State, Country'.")
            return
        location = formatted_location
    if start_date and end_date:
        historical_data = get_historical_weather(location, start_date, end_date)
        if historical_data:
            display_weather_in_gui(historical_data, is_historical=True)
            for day in historical_data.get('days', []):
                temperature = f"{day.get('temp', 'N/A')}°F"
                create_record(location, day.get('datetime', ''), temperature)
            display_records()
        else:
            messagebox.showerror("Error", "Unable to fetch historical weather data.")
    else:
        weather_data, forecast_data = get_weather(API_KEY, location)
        if weather_data and forecast_data:
            display_weather_in_gui(weather_data, forecast_data)
            temperature = f"{weather_data['main'].get('temp', 'N/A')}°F"
            create_record(location, datetime.now().strftime("%Y-%m-%d"), temperature)
            display_records()
        else:
            messagebox.showerror("Error", "Unable to fetch weather data.")

# ======================================================================
# Function to Load Saved Weather Data When a Record is Double-Clicked
# ======================================================================
def on_record_double_click(event):
    selected = tree.selection()
    if not selected:
        return
    record_id = tree.item(selected[0], "values")[0]
    conn = sqlite3.connect("weather_app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weather_requests WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    conn.close()
    if record:
        location = record[1]
        date = record[2]
        if date == datetime.now().strftime("%Y-%m-%d"):
            weather_data, forecast_data = get_weather(API_KEY, location)
            if weather_data and forecast_data:
                display_weather_in_gui(weather_data, forecast_data)
        else:
            historical_data = get_historical_weather(location, date, date)
            if historical_data:
                display_weather_in_gui(historical_data, is_historical=True)

# ========================================
# GUI Setup and Main Application Window
# ========================================
root = tk.Tk()
root.title("Advanced Weather App - by Vraj Amin")
root.configure(bg=BACKGROUND)
root.attributes("-fullscreen", True)

header_frame = tk.Frame(root, bg=PRIMARY, padx=10, pady=10)
header_frame.pack(fill="x")
tk.Label(header_frame, text="Advanced Weather App - by Vraj Amin",
         font=("Helvetica", 20, "bold"), bg=PRIMARY, fg=TEXT_ON_PRIMARY).pack(side="left")
tk.Button(header_frame, text="Info", command=show_info, font=("Helvetica", 12), bg=PRIMARY_VARIANT, fg=TEXT_ON_PRIMARY).pack(side="right")

input_container = RoundedFrame(root, corner_radius=15, padding=10, bg_color=BACKGROUND)
input_container.pack(fill="x", padx=20, pady=10)
tk.Label(input_container.frame, text="Enter Location (City, State, Country) or 'auto':",
         font=("Helvetica", 12), bg=BACKGROUND, fg=TEXT_ON_SURFACE).grid(row=0, column=0, sticky="w")
location_entry = tk.Entry(input_container.frame, font=("Helvetica", 12), width=30)
location_entry.grid(row=1, column=0, pady=5, sticky="w")
tk.Label(input_container.frame, text="Start Date (YYYY-MM-DD):",
         font=("Helvetica", 12), bg=BACKGROUND, fg=TEXT_ON_SURFACE).grid(row=0, column=1, sticky="w", padx=10)
start_date_entry = tk.Entry(input_container.frame, font=("Helvetica", 12), width=15)
start_date_entry.grid(row=1, column=1, pady=5, sticky="w", padx=10)
tk.Label(input_container.frame, text="End Date (YYYY-MM-DD):",
         font=("Helvetica", 12), bg=BACKGROUND, fg=TEXT_ON_SURFACE).grid(row=0, column=2, sticky="w", padx=10)
end_date_entry = tk.Entry(input_container.frame, font=("Helvetica", 12), width=15)
end_date_entry.grid(row=1, column=2, pady=5, sticky="w", padx=10)
fetch_button = tk.Button(input_container.frame, text="Fetch Weather", font=("Helvetica", 12),
                         command=fetch_weather, bg=SURFACE, fg=TEXT_ON_PRIMARY, padx=10, pady=5)
fetch_button.grid(row=1, column=3, padx=10)

output_frame = tk.Frame(root, bg=BACKGROUND, padx=5, pady=5)
output_frame.pack(fill="both", expand=True)
for i in range(6):
    output_frame.columnconfigure(i, weight=1)

records_frame = tk.Frame(root, bg=BACKGROUND, padx=10, pady=10)
records_frame.pack(fill="both", expand=True)
tree = ttk.Treeview(records_frame, columns=("ID", "Location", "Date", "Temperature"), show="headings")
tree.heading("ID", text="ID")
tree.heading("Location", text="Location")
tree.heading("Date", text="Date")
tree.heading("Temperature", text="Temperature")
tree.pack(fill="both", expand=True)

# ========================================
# Function to Display Saved Weather Records in the GUI Table
# ========================================
def display_records():
    for row in tree.get_children():
        tree.delete(row)
    records = read_records()
    for record in records:
        tree.insert("", "end", values=record)

display_records()
tree.bind("<Double-1>", on_record_double_click)

def update_selected_record():
    selected = tree.selection()
    if not selected:
        messagebox.showerror("Error", "Please select a record to update.")
        return
    record_id = tree.item(selected[0], "values")[0]
    new_temp = simpledialog.askstring("Update Temperature", "Enter new temperature:")
    if new_temp:
        update_record(record_id, new_temp)
        display_records()

def delete_selected_record():
    selected = tree.selection()
    if not selected:
        messagebox.showerror("Error", "Please select a record to delete.")
        return
    record_id = tree.item(selected[0], "values")[0]
    delete_record(record_id)
    display_records()

button_frame = tk.Frame(root, bg=BACKGROUND, padx=10, pady=10)
button_frame.pack(fill="x")
update_button = tk.Button(button_frame, text="Update Selected", font=("Helvetica", 12),
                          command=update_selected_record, bg=SURFACE, fg=TEXT_ON_PRIMARY, padx=10, pady=5)
update_button.pack(side="left", padx=5)
delete_button = tk.Button(button_frame, text="Delete Selected", font=("Helvetica", 12),
                          command=delete_selected_record, bg=SURFACE, fg=TEXT_ON_PRIMARY, padx=10, pady=5)
delete_button.pack(side="left", padx=5)

root.mainloop()
