from tendo import singleton
me = singleton.SingleInstance()

import threading
import os
import sys
import time
import logging
import tempfile
from pathlib import Path
from typing import Optional
import requests
import pyperclip
import keyboard
from PIL import ImageGrab, Image
from win32com.client import Dispatch
from tkinter import Tk, simpledialog, messagebox, Label
from win32gui import GetWindowText, GetForegroundWindow
import subprocess

import Config
import Maple

# Constants
SCRIPT_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent

CONFIG_PATH = SCRIPT_DIR / "config.json"
DEFAULT_MAPLE_PATH = r"C:\Program Files\Maple 2025\bin.X86_64_WINDOWS\cmaple.exe"
LOG_FILE = SCRIPT_DIR / 'latex_to_maple.log'

# Setup logging
tlogging = logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
        
def has_internet(url="https://www.google.com", timeout=3) -> bool:
    try:
        requests.head(url, timeout=timeout)
        return True
    except requests.RequestException:
        return False

def prompt_maple_path() -> Optional[str]:
    root = Tk()
    root.withdraw()
    path = simpledialog.askstring("Maple Path", 
        "Maple executable not found.\nPlease enter full path to cmaple.exe:")
    root.destroy()
    return path

def get_maple_executable() -> str:
    logging.debug("Attempting to load config")
    cfg = Config.load_config(CONFIG_PATH)
    path = cfg.get('maple_exe', DEFAULT_MAPLE_PATH)
    while not Path(path).is_file():
        logging.warning(f"Maple not found at {path}. Prompting user.")
        path = prompt_maple_path()
        if not path:
            messagebox.showerror("Error", "Maple path is required. Exiting.")
            logging.error("No path provided, exiting.")
            sys.exit(1)
        if Path(path).is_file():
            cfg['maple_exe'] = path
            Config.save_config(CONFIG_PATH, cfg)
        else:
            messagebox.showwarning("Invalid Path", f"No file found at {path}. Try again.")
    logging.info(f"Using Maple executable at {path}")
    return path

def paste_at_cursor(text: str, truncate: bool) -> bool:
    try:
        pyperclip.copy(text)
        time.sleep(0.06)
        keyboard.press_and_release('ctrl+v')
        logging.debug("Logged at cursor: %s", text)
        return False
    except Exception:
        logging.exception("Failed in log_at_cursor")
        return True

def create_startup():
    task_name = "ImageToMapleStartup"
    
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
    else:
        script_path = os.path.abspath(sys.argv[0])
        command = f'"{sys.executable}" "{script_path}"'
        
    result = subprocess.run(
        ["schtasks", "/query", "/tn", task_name],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

    if "ERROR" in result.stdout or "ERROR" in result.stderr:
        logging.info("Scheduled task not found. Creating new task...")
        subprocess.run([
            "schtasks",
            "/create",
            "/tn", task_name,
            "/tr", command,
            "/sc", "onlogon",
            "/delay", "0000:10",
            "/rl", "highest",
            "/it",
        ], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        ps_script = f"""
        $task = Get-ScheduledTask -TaskName "{task_name}"
        $task.Settings.DisallowStartIfOnBatteries = $false
        $task.Settings.StopIfGoingOnBatteries = $false
        Set-ScheduledTask $task
        """
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        logging.info("Scheduled task created successfully.")
    else:
        logging.info("Scheduled task already exists. Skipping creation.")

def initiate_loading_popup():
    global hidepopupwindow
    root = Tk()
    root.wm_attributes("-topmost", 1)
    root.overrideredirect(True)
    
    window_width = 150
    window_height = 40
    screen_width = root.winfo_screenwidth()
    x = (screen_width - window_width) // 2
    y = 50
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    l = Label(root, text = "Loading...", font=("Arial", 20))
    l.pack()
    root.withdraw()
    
    while True:
        time.sleep(0.02)
        if hidepopupwindow==False:
            if root.state() == 'withdrawn':
                root.deiconify()
        else:
            root.withdraw()
        root.update()
        
def ping_server():
    while True:
        try:
            requests.get("https://image2maple.onrender.com/")
        except Exception as e:
            logging.error(f"Ping server failed: {e}")
        time.sleep(180)

def image_to_maple(maple_exe: str, raw: bool = False):
    logging.info("Shortcut pressed.")
    global hidepopupwindow
    window_text = GetWindowText(GetForegroundWindow())
    if not "Maple" in window_text and not "Word" in window_text:
        logging.warning("Maple or word window not active, skipping paste.")
        return
    
    if not has_internet():
        logging.error("No internet connection.")
        return

    while any(keyboard._pressed_events):  # type: ignore
        time.sleep(0.01)
    
    hidepopupwindow=False
    
    img = ImageGrab.grabclipboard()
    time.sleep(0.05)
    if not isinstance(img, Image.Image):
        logging.error("Clipboard does not contain an image.")
        hidepopupwindow=True
        return
    buf = tempfile.SpooledTemporaryFile()
    img.save(buf, format='PNG'); buf.seek(0)
    time.sleep(0.05)
    
    logging.info("Clipboard condains image.")
    logging.debug("Sending image to image2maple render backend...")
    
    files = {'file': ('image.png', buf.read(), 'image/png')}
    response = requests.post("https://image2maple.onrender.com/imagetolatex", files=files)
    latex = response.json().get('latex', '') if response.status_code == 200 else ''
    
    if latex=="":
        logging.error("OCR returned empty string.")
        hidepopupwindow=True
        return
    
    logging.info("Image to latex successful.")
    logging.debug("Converting latex to MathML...")
    
    mathml = Maple.latex_to_mathml( latex, maple_exe, raw )
    
    hidepopupwindow=True
    
    logging.info("Success! Converted latex converted to MathML.")
    
    if paste_at_cursor(mathml, True):
        logging.info("Pasted MathML to cursor.")
    else:
        logging.info("Skipped pasting of MathML to cursor.")

def main():
    global hidepopupwindow
    hidepopupwindow=True
    
    logging.info("Starting...")
    
    maple = get_maple_executable()
    
    thread = threading.Thread(target=initiate_loading_popup, daemon=True)
    thread.start()
    
    thread = threading.Thread(target=ping_server, daemon=True)
    thread.start()
    
    create_startup()
    
    #keyboard.add_hotkey('ctrl+alt+v', lambda: process_clipboard(maple, False))
    keyboard.add_hotkey('ctrl+shift+alt+v', lambda: image_to_maple(maple, True))
        
    logging.info("Running...")
    keyboard.wait()

if __name__ == '__main__':
    main()