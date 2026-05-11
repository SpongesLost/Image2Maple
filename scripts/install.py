import config
import version
import tkinter as tk
from tkinter import ttk
import keyboard
import sys
import os
import subprocess

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

keybind = ""
record_keybind = False
exitFlag = False

def _get_task(task_name):
    result = subprocess.run(
            ["schtasks", "/query"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    return [x for x in result.stdout.splitlines() if task_name in x]

def is_installed(task_name="ImageToMapleStartup") -> bool:
    try:
        tasks = _get_task(task_name)
        return not len(tasks) == 0
    except:
        return False

def is_version(version : str, task_name="ImageToMapleStartup"):
    try:
        result = subprocess.run(
            ["schtasks", "/query"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        tasks = [x for x in result.stdout.splitlines() if task_name in x]
        if len(tasks)==0:
            return False
        return tasks[0].split("    ")[0].split(" ")[1]==version
    except:
        return False

def install():
    global exitFlag
    def check_keybind():
        global keybind, record_keybind
        
        if record_keybind:
            hotkey = keyboard.get_hotkey_name()
            if hotkey == "enter":
                keybind_button.config(bg=DEFAULT_BUTTON_COLOR)
                record_keybind = False
                if keybind_button["text"] == "Waiting for keypress...":
                    keybind_button.config(text="Press to record keybind...")
            elif len(hotkey) == 0:
                keybind = ""
            elif len(hotkey) > len(keybind):
                keybind = hotkey
                keybind_button.config(text=keybind)
        
        if not exitFlag:
            root.after(50, check_keybind)

    def bind_button():
        global record_keybind
        if not record_keybind:
            record_keybind = True
            keybind_button.config(text="Waiting for keypress...", bg="light gray")
        else:
            record_keybind = False
            keybind_button.config(bg=DEFAULT_BUTTON_COLOR)
            if keybind_button["text"] == "Waiting for keypress...":
                keybind_button.config(text="Press to record keybind...")
    
    def start():
        global exitFlag
        cfg = config.load_config(config.DEFAULT_CONFIG_PATH)
        cfg["start_up"] = bool(var.get())
        if keybind_button["text"] == "Waiting for keypress..." or keybind_button["text"] == "Press to record custom keybind...":
            cfg["keybind"] = "ctrl+alt+shift+v"
        else:
            cfg["keybind"] = keybind_button["text"]
        config.save_config(config.DEFAULT_CONFIG_PATH, cfg)
        exitFlag = True
        root.destroy()
                
    root = tk.Tk()
    root.title("ImageToMaple Setup")
    root.resizable(False, False)
    root.attributes('-fullscreen', False)
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)
    img=tk.PhotoImage(master=root, file=resource_path("ImageToMaple.png"))
    root.iconphoto(False,img)

    window_width = 500
    window_height = 175
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = round((screen_height - window_height) // 2.2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    tk.Label(root, text=f"Configure ImageToMaple v{version.__version__} (64 bit)",font=("Arial", 16), justify="center").pack( padx=10,pady=(0,10), anchor="n")
    tk.Label(root, text="Here you can configure how ImageToMaple should behave.\nYour choices are stored in a config file along with this exe.", justify="left").pack( padx=10, anchor="w")

    keybind_frame = tk.Frame(root)
    keybind_frame.pack(padx=10, pady=(10,0), anchor="w", fill="x")

    tk.Label(keybind_frame, text="Keybind:", font=("Arial", 11)).pack(side="left", padx=(0, 3))

    keybind_button = tk.Button(keybind_frame, text="Press to record custom keybind...", width=30, height=1, command=bind_button, justify="center")
    DEFAULT_BUTTON_COLOR = keybind_button["bg"]
    keybind_button.pack(side="left")
    tk.Label(root, text="(default: ctrl+alt+shift+v)", justify="left").pack( padx=10, pady=0, anchor="w")
    
    root.after(50, check_keybind)

    var = tk.IntVar()
    checkbutton = ttk.Checkbutton(root, text="Start at login", variable=var, onvalue=1, offvalue=0)
    checkbutton.pack(padx=10, pady=10, anchor="sw", side="left")
    
    install_button = tk.Button(text="Start", width=10, height=1, command=start)
    install_button.pack(padx=10, pady=10, anchor="se", side="bottom")

    root.mainloop()
    return exitFlag

if __name__ == '__main__':
    install()