from tendo import singleton
me = singleton.SingleInstance()

import logging
import os
from pathlib import Path
import sys
import signal
import version
# Constants
SCRIPT_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
print(SCRIPT_DIR)
DEFAULT_MAPLE_PATH = r"C:\Program Files\Maple 2025\bin.X86_64_WINDOWS\cmaple.exe"
LOG_FILE = SCRIPT_DIR / 'imagetomaple.log'
print(LOG_FILE)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logging.info("Starting ImageToMaple "+version.__version__)

import install
import threading
import time
import tempfile
from typing import Optional
import requests
import pyperclip
import keyboard
from PIL import ImageGrab, Image
from tkinter import Tk, simpledialog, messagebox, Label, PhotoImage
from win32gui import GetWindowText, GetForegroundWindow
import subprocess
import maple
import pystray
from uninstallimagetomaple import uninstall_imagetomaple

import config
CONFIG = config.load_config(config.DEFAULT_CONFIG_PATH)
tray_icon = None
        
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
    path = CONFIG.get('maple_exe', DEFAULT_MAPLE_PATH)
    while not (os.path.isfile(path) and os.path.basename(path) == "cmaple.exe"):
        logging.warning(f"Maple not found at {path}. Prompting user.")
        path = prompt_maple_path()
        if not path:
            messagebox.showerror("Error", "Maple path is required. Exiting.")
            logging.error("No path provided, exiting.")
            sys.exit(1)
        if os.path.isfile(path) and os.path.basename(path) == "cmaple.exe":
            CONFIG['maple_exe'] = path
            config.save_config(config.DEFAULT_CONFIG_PATH, CONFIG)
        else:
            messagebox.showwarning("Invalid Path", f"No file found at {path}. Try again.")
    logging.info(f"Using Maple executable at {path}")
    return path

def paste_at_cursor(text: str) -> bool:
    try:
        pyperclip.copy(text)
        time.sleep(0.06)
        keyboard.press_and_release('ctrl+v')
        logging.debug("Logged at cursor: %s", text)
        return True
    except Exception:
        logging.exception("Failed in log_at_cursor")
        return False
    
def create_tray_icon():
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "ImageToMaple.png")
        image = Image.open(icon_path)
    except Exception as e:
        print(f"Could not load icon: {e}")
        image = Image.new('RGB', (64, 64), color='blue')
    
    menu = pystray.Menu(
        pystray.MenuItem("Quit", quit_application)
    )
    
    icon = pystray.Icon("SchoolFileSearch", image, "School File Search", menu)
    logging.info("Tray icon successfully created")
    return icon

def quit_application(icon=None, item=None):
    logging.info("Shutting down...")
    
    def delayed_shutdown():
        global hidepopupwindow, tray_icon
        try:
            hidepopupwindow = True
            keyboard.unhook_all()
            logging.info("Keyboard hooks removed")
            
            if icon:
                icon.stop()
                logging.info("Tray icon stopped (parameter)")
            elif 'tray_icon' in globals() and tray_icon:
                tray_icon.stop() # type: ignore
                logging.info("Tray icon stopped (global)")
            
            time.sleep(0.2)
            
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")
        finally:
            logging.info("Exiting application")
            os._exit(0)
     
    shutdown_thread = threading.Thread(target=delayed_shutdown, daemon=True)
    shutdown_thread.start()

def run_tray_icon():
    global tray_icon
    logging.info("Creating tray icon...")
    try:
        tray_icon = create_tray_icon()
        tray_icon.run()
    except Exception as e:
        logging.exception(f"Tray icon could not be created: {e}")

def create_startup():
    if not getattr(sys, "frozen", False):
        logging.info("File is not an executable skipping startup code")
        return
    
    task_name = "ImageToMapleStartup "+version.__version__
    
    command = f'"{sys.executable}"'
        
    result = subprocess.run(
        f'schtasks /query /tn "{task_name}" /v /fo LIST | find "Task To Run:"',
        shell=True,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    )

    if not ("ERROR" in result.stdout or "ERROR" in result.stderr):
        path_to_application = result.stdout.replace("Task To Run:","").strip()
        if not path_to_application==command:
            logging.warning("Schtask path doesnt match current path")
            logging.info("Deleting current schtask and creating a new task")
            subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            result.stdout="ERROR"

    if "ERROR" in result.stdout or "ERROR" in result.stderr:
        logging.info("Scheduled task not found. Creating new task...")
        subprocess.run(
            [
            "schtasks",
            "/create",
            "/tn", task_name,
            "/tr", command,
            "/sc", "onlogon",
            "/delay", "0000:10",
            "/rl", "highest",
            "/it",
            ], 
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        ps_script = f"""
        $task = Get-ScheduledTask -TaskName "{task_name}"
        $task.Settings.DisallowStartIfOnBatteries = $false
        $task.Settings.StopIfGoingOnBatteries = $false
        Set-ScheduledTask $task
        """
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        logging.info("Scheduled task created successfully.")
    else:
        logging.info("Scheduled task already exists. Skipping creation.")

def create_loading_popup():
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
        logging.warning("Maple or word window not active, skipping image_to_maple.")
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
    
    mathml = maple.latex_to_mathml( latex, maple_exe, raw )
    
    hidepopupwindow=True
    
    logging.info("Success! Converted latex converted to MathML.")
    
    if paste_at_cursor(mathml):
        logging.info("Pasted MathML to cursor.")
    else:
        logging.info("Skipped pasting of MathML to cursor.")

def main():
    global hidepopupwindow, CONFIG
    hidepopupwindow=True
    logging.info("Starting...")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, lambda sig, frame: quit_application())
    signal.signal(signal.SIGINT, lambda sig, frame: quit_application())
    
    # Windows-specific shutdown handling
    if os.name == 'nt':
        try:
            import win32api
            def windows_shutdown_handler(dwCtrlType):
                logging.info("Windows shutdown signal received")
                quit_application()
                return True
            win32api.SetConsoleCtrlHandler(windows_shutdown_handler, True)
        except ImportError:
            logging.warning("win32api not available, limited shutdown handling")
    
    maple = get_maple_executable()
    
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    loading_thread = threading.Thread(target=create_loading_popup, daemon=True)
    loading_thread.start()
    
    if "start_up" in CONFIG:
        if CONFIG["start_up"]:
            create_startup()

    ping_thread = threading.Thread(target=ping_server, daemon=True)
    ping_thread.start()
    
    #keyboard.add_hotkey('ctrl+alt+v', lambda: process_clipboard(maple, False))
    keyboard.add_hotkey(CONFIG["keybind"] if "keybind" in CONFIG else "ctrl+alt+shift+v", lambda: image_to_maple(maple, True))
  
    logging.info("Running...")
    keyboard.wait()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def handle_install():
    global CONFIG
    if install.is_installed():
        if install.is_version(version.__version__):
            return True
        else:
            root = Tk()
            root.wm_attributes("-topmost", 1)
            root.withdraw()
            confirmed=messagebox.askquestion('Uninstall Application', 'A different version of ImageToMaple is currently installed\nDo you want to uninstall it and install this instance instead?', parent=root)
            root.destroy()
            if confirmed=="yes":
                uninstall_imagetomaple(True)
            else:
                return False
    cfg = install.install()
    if not cfg:
        logging.warning("Setup aborted.")
        return False
    CONFIG = config.load_config(config.DEFAULT_CONFIG_PATH)
    return True

if __name__ == '__main__':
    if handle_install():
        main()