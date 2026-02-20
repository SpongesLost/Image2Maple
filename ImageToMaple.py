import threading
from tendo import singleton
me = singleton.SingleInstance()

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
    logging.debug("Checking for Maple executable")
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
    logging.debug("Attempting to create startup shortcut")
    try:
        script_path = os.path.abspath(sys.argv[0])
        startup_dir = os.path.join(os.environ.get('APPDATA', ''), r"Microsoft\Windows\Start Menu\Programs\Startup")
        shortcut_path = os.path.join(startup_dir, "ImageToMaple.lnk")
        if not os.path.exists(shortcut_path):
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(shortcut_path)
            shortcut.TargetPath = sys.executable
            shortcut.Arguments = f'"{script_path}"'
            shortcut.WorkingDirectory = os.path.dirname(script_path)
            shortcut.IconLocation = script_path
            shortcut.Save()
            logging.info("Startup shortcut created at %s", shortcut_path)
        else: 
            logging.info("Startup shortcut already exists at %s", shortcut_path)
    except Exception:
        logging.exception("Failed to create startup shortcut")

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

def process_clipboard(maple_exe: str, raw: bool = False):
    global hidepopupwindow
    window_text = GetWindowText(GetForegroundWindow())
    if not "Maple" in window_text and not "Word" in window_text:
        logging.warning("Maple or word window not active, skipping paste.")
        return

    while any(keyboard._pressed_events):  # type: ignore
        time.sleep(0.01)
        
    if not has_internet():
        logging.error("No internet connection.")
        return
    
    hidepopupwindow=False
    
    img = ImageGrab.grabclipboard()
    time.sleep(0.05)
    if not isinstance(img, Image.Image):
        hidepopupwindow=True
        return
    buf = tempfile.SpooledTemporaryFile()
    img.save(buf, format='PNG'); buf.seek(0)
    time.sleep(0.05)
    
    files = {'file': ('image.png', buf.read(), 'image/png')}
    response = requests.post("http://127.0.0.1:8000/imagetolatex", files=files)
    latex = response.json().get('latex', '') if response.status_code == 200 else ''
    
    if latex=="":
        logging.error("OCR returned empty string")
        hidepopupwindow=True
        return
    mathml = Maple.latex_to_mathml( latex, maple_exe, raw )
    
    hidepopupwindow=True
    
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
    
    create_startup()
    
    #keyboard.add_hotkey('ctrl+alt+v', lambda: process_clipboard(maple, False))
    keyboard.add_hotkey('ctrl+shift+alt+v', lambda: process_clipboard(maple, True))
        
    logging.info("Running...")
    keyboard.wait()

if __name__ == '__main__':
    main()