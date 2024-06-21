import os
import json
import tkinter as tk
from tkinter import ttk
import psutil
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
from PIL import Image, ImageTk
from icoextract import IconExtractor

# Constants for file paths and icon sizes
VOLUME_SETTINGS_FILE = 'volume_settings.json'
DEFAULT_ICON_FILE = 'default_icon.png'
ICON_SIZE = (32, 32)
ICONS_DIR = 'icons'

# Ensure the icons directory exists
os.makedirs(ICONS_DIR, exist_ok=True)

# Ensure the volume settings file exists
if not os.path.exists(VOLUME_SETTINGS_FILE):
    with open(VOLUME_SETTINGS_FILE, 'w') as file:
        json.dump({}, file)

# Ensure the default icon file exists
default_icon_path = os.path.join(ICONS_DIR, DEFAULT_ICON_FILE)
if not os.path.exists(default_icon_path):
    # Create a blank default icon
    default_icon = Image.new("RGBA", ICON_SIZE, (255, 255, 255, 0))
    default_icon.save(default_icon_path)


class VolumeControlApp:
    def __init__(self, root):
        """Initialize the VolumeControlApp with root window."""
        self.root = root
        self.root.title("Volume Mixer")
        self.root.geometry("800x400")

        self.frames = {}
        self.icons = {}
        self.volume_settings = self.load_volume_settings()
        self.create_widgets()
        self.update_audio_sessions()
        self.periodic_update()

        self.root.bind("<Configure>", self.on_resize)

    def create_widgets(self):
        """Create and arrange the main UI widgets."""
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.pack_propagate(False)

        self.canvas = tk.Canvas(self.frame)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="top", fill="both", expand=True)
        self.scrollbar.pack(side="bottom", fill="x")

    def load_volume_settings(self):
        """Load volume settings from a JSON file."""
        try:
            with open(VOLUME_SETTINGS_FILE, 'r') as file:
                return json.load(file)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading volume settings: {e}")
            return {}

    def save_volume_settings(self):
        """Save volume settings to a JSON file."""
        try:
            with open(VOLUME_SETTINGS_FILE, 'w') as file:
                json.dump(self.volume_settings, file)
        except IOError as e:
            print(f"Error saving volume settings: {e}")

    def update_audio_sessions(self):
        """Update the list of active audio sessions."""
        try:
            current_sessions = {session.Process.name() if session.Process else "System Sounds"
                                for session in AudioUtilities.GetAllSessions()}
        except Exception as e:
            print(f"Error fetching audio sessions: {e}")
            current_sessions = set()

        displayed_sessions = set(self.frames.keys())

        # Add new sessions
        for session in current_sessions - displayed_sessions:
            self.create_volume_slider(session)

        # Remove sessions that are no longer active
        for session in displayed_sessions - current_sessions:
            self.frames[session].destroy()
            del self.frames[session]

    def create_volume_slider(self, app_name):
        """Create a volume slider for a given application."""
        frame = tk.Frame(self.scrollable_frame)
        frame.pack(side="left", padx=10, pady=10, fill=tk.Y, expand=True)
        self.frames[app_name] = frame

        normalized_name = app_name.replace(' ', '_').replace('.', '_')
        icon_path = os.path.join(ICONS_DIR, f"{normalized_name}.ico")

        if not os.path.exists(icon_path):
            self.download_icon(app_name, icon_path)

        self.load_icon(frame, app_name, icon_path)

        label = tk.Label(frame, text=app_name)
        label.pack()

        session = self.get_session_by_name(app_name)
        if session:
            volume_slider = ttk.Scale(frame, from_=0, to=100, orient="vertical",
                                      command=lambda v, s=session, a=app_name: self.on_volume_change(s, v, a))
            volume_slider.pack(fill=tk.Y, expand=True)

            volume = self.volume_settings.get(app_name, self.get_volume(session) * 100)
            volume_slider.set(volume)

    def get_session_by_name(self, app_name):
        """Retrieve audio session by application name."""
        for session in AudioUtilities.GetAllSessions():
            if (session.Process and session.Process.name() == app_name) or (not session.Process and app_name == "System Sounds"):
                return session
        return None

    def download_icon(self, app_name, icon_path):
        """Download the icon for the application."""
        try:
            executable_path = self.find_executable_path(app_name)
            if executable_path:
                self.extract_icon(executable_path, icon_path)
        except Exception as e:
            print(f"Error downloading icon for {app_name}: {e}")

    def find_executable_path(self, app_name):
        """Find the executable path of the given application."""
        for proc in psutil.process_iter(['name', 'exe']):
            if proc.info['name'] == app_name:
                return proc.info['exe']
        return None

    def extract_icon(self, exe_path, save_path):
        """Extract the icon from the executable and save it."""
        extractor = IconExtractor(exe_path)
        try:
            extractor.export_icon(save_path)
        except Exception as e:
            print(f"Error extracting icon from {exe_path}: {e}")

    def load_icon(self, frame, app_name, icon_path):
        """Load the icon for the application and display it."""
        if os.path.exists(icon_path):
            try:
                image = Image.open(icon_path)
                image = image.resize(ICON_SIZE, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.icons[app_name] = photo
                icon_label = tk.Label(frame, image=photo)
                icon_label.image = photo
                icon_label.pack()
                print(f"Loaded icon for {app_name}")
            except Exception as e:
                print(f"Error loading icon for {app_name}: {e}")
                self.load_default_icon(frame, app_name)
        else:
            print(f"Icon for {app_name} could not be downloaded.")
            self.load_default_icon(frame, app_name)

    def load_default_icon(self, frame, app_name):
        """Load the default icon if no specific icon is available."""
        try:
            image = Image.open(default_icon_path)
            image = image.resize(ICON_SIZE, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.icons[app_name] = photo
            if frame:
                icon_label = tk.Label(frame, image=photo)
                icon_label.image = photo
                icon_label.pack()
            print(f"Loaded default icon for {app_name}")
        except Exception as e:
            print(f"Error loading default icon for {app_name}: {e}")

    def on_volume_change(self, session, volume, app_name):
        """Handle volume change events."""
        try:
            volume_level = float(volume) / 100
            self.set_volume(session, volume_level)
            self.volume_settings[app_name] = volume
            self.save_volume_settings()
        except Exception as e:
            print(f"Error changing volume for {app_name}: {e}")

    def get_volume(self, session):
        """Get the current volume level of the session."""
        try:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            return volume.GetMasterVolume()
        except Exception as e:
            print(f"Error getting volume for session: {e}")
            return 0

    def set_volume(self, session, volume_level):
        """Set the volume level for the session."""
        try:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            volume.SetMasterVolume(volume_level, None)
        except Exception as e:
            print(f"Error setting volume for session: {e}")

    def periodic_update(self):
        """Periodically update the audio sessions."""
        self.update_audio_sessions()
        self.root.after(1000, self.periodic_update)

    def on_resize(self, event):
        """Handle window resize events."""
        for frame in self.frames.values():
            for widget in frame.winfo_children():
                if isinstance(widget, ttk.Scale):
                    widget.config(length=self.root.winfo_height() - 100)


if __name__ == "__main__":
    root = tk.Tk()
    app = VolumeControlApp(root)
    root.mainloop()
