import os
from pathlib import Path
import sys
import psutil
from win32com.client import Dispatch
import subprocess
import tkinter as tk
from tkinter import ttk
import time
import files

def update_status(message, *progressvalue : int):
    status_label.config(text=message)
    microstatus_label.insert(tk.END, message+"\n")
    if progressvalue:
        progress.config(mode='determinate', value=progressvalue[0])
    root.update()
    print(message)

def update_microstatus(message, *progressvalue : int):
    microstatus_label.insert(tk.END, message+"\n")
    microstatus_label.see(tk.END)  # Scroll to bottom
    if progressvalue:
        progress.config(mode='determinate', value=progressvalue[0])
    root.update()
    print(message)
    with open("uninstall_log.txt", "w") as f:
        f.write("ImageToMaple Uninstall Log\n")
        f.write("=" * 30 + "\n")
        f.write(microstatus_label.get("1.0", tk.END))

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def uninstall_using_scheduledtask(task_name="ImageToMapleStartup"):
    try:
        update_microstatus("Looking for scheduledtask...")
        result = subprocess.run(
            ["schtasks", "/query"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        tasks = [x for x in result.stdout.splitlines() if task_name in x]
        task_name = tasks[0].split("   ")[0]
            
        if "ERROR" not in result.stdout and "ERROR" not in result.stderr:
            update_microstatus(f"Found scheduled task: {task_name}")
            result = subprocess.run(
                f'schtasks /query /tn "{task_name}" /v /fo LIST | find "Task To Run:"',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            path_to_application = result.stdout.replace("Task To Run:","").strip().strip('\"')
            update_microstatus(f"Task points to: '{path_to_application}'")
            subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"], 
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            try:
                if os.path.exists(path_to_application):
                    remove_target_file_config_and_log(path_to_application)
                else:
                    update_microstatus(f"Scheduled task does not point to existing path {path_to_application}")
            except Exception as e:
                update_microstatus(f"Error during killing process: {e}")
        else:
            update_microstatus(f"No scheduled task named {task_name} found.")
            
    except Exception as e:
        update_microstatus(f"Error removing scheduled task {task_name}: {e}")

def remove_target_file_config_and_log(path):
    try:
        target_dir = os.path.dirname(path)
        config_path = os.path.join(target_dir, "config.json")
        if os.path.exists(config_path):
            os.remove(config_path)
            update_microstatus(f"Deleted config file: {config_path}")
        else:
            update_microstatus(f"No config.json found at {config_path}")
        log_path = os.path.join(target_dir, "imagetomaple.log")
        if os.path.exists(log_path):
            os.remove(log_path)
            update_microstatus(f"Deleted log file: {log_path}")
        else:
            update_microstatus(f"No imagetomaple.log found at {log_path}")
            log_path = os.path.join(target_dir, "latex_to_maple.log")
            if os.path.exists(log_path):
                os.remove(log_path)
                update_microstatus(f"Deleted log file: {log_path}")
            else:
                update_microstatus(f"No latex_to_maple.log found at {log_path}")
            
        os.remove(path)
        update_microstatus(f"Deleted target script file: {path}")
    except Exception as e:
        update_microstatus(f"Failed to delete target, config or log file: {e}")

def uninstall_using_startup_script():
    startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
    shortcut_path = os.path.join(startup_dir, "ImageToMaple.lnk")

    if os.path.exists(shortcut_path):
        update_microstatus("Removing depricated startup script and target files...")
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(shortcut_path)
            target_path = shortcut.TargetPath   # usually python.exe
            arguments = shortcut.Arguments      # usually the script path
            update_microstatus(f"Found startup shortcut: {shortcut_path}")
            update_microstatus(f"Shortcut points to: {target_path}")
            update_microstatus(f"Shortcut arguments: {arguments}")
            
            os.remove(shortcut_path)
            update_microstatus(f"Deleted startup shortcut: {shortcut_path}")
            if arguments:
                script_path = arguments.strip('"')
                if os.path.exists(script_path) and os.path.isfile(script_path):
                    remove_target_file_config_and_log(script_path)
                else:
                    update_microstatus(f"Target script file does not exist or is not a file: {script_path}")
            else:
                update_microstatus("No arguments found in shortcut to delete.")
                if "ImageToMaple" in target_path:
                    update_microstatus(f"Identified 'ImageToMaple' in target path: {target_path}")
                    if os.path.exists(target_path) and os.path.isfile(target_path):
                        remove_target_file_config_and_log(target_path)
            return True
        except Exception as e:
            update_microstatus(f"Error handling shortcut: {e}")
            return False
    else:
        update_microstatus("Depricated startup shortcut not found.")
        return False

def kill_process_and_children(proc, exclude_pid=None):
    try:
        children = proc.children(recursive=True)
        for child in children:
            # Skip killing the excluded PID even if it's a child
            if exclude_pid and child.pid == exclude_pid:
                update_microstatus(f"Skipping child process {child.pid} (excluded)")
                continue
            update_microstatus(f"Terminating child process {child.pid}")
            child.terminate()
        proc.terminate()
        proc.wait(timeout=5)
    except psutil.TimeoutExpired:
        update_microstatus(f"Process {proc.pid} did not terminate, killing now")
        proc.kill()
    except Exception as e:
        update_microstatus(f"Error killing process {proc.pid}: {e}")

def kill_running_script(script_name, exe_name=None, exclude_current_pid=False):
    found = False
    current_pid = os.getpid() if exclude_current_pid else None
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process if exclusion is requested
            if current_pid and proc.pid == current_pid:
                update_microstatus(f"Skipping current process {proc.pid}")
                continue
                
            proc_name = proc.info['name'].lower() if proc.info['name'] else ''
            cmdline = proc.info['cmdline'] or []

            if 'python' in proc_name:
                # Check if any argument matches the script filename exactly (case-insensitive)
                if any(os.path.basename(arg).lower() == script_name.lower() for arg in cmdline):
                    update_microstatus(f"Killing python process {proc.pid} running {script_name}")
                    kill_process_and_children(proc, exclude_pid=current_pid)
                    found = True
            elif exe_name and proc_name == exe_name.lower():
                update_microstatus(f"Killing executable process {proc.pid} named {exe_name}")
                kill_process_and_children(proc, exclude_pid=current_pid)
                found = True
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            update_microstatus(f"Access denied to process {proc.pid}")
        except Exception as e:
            update_microstatus(f"Unexpected error with process {proc.pid}: {e}")

    if not found:
        update_microstatus(f"No running process found for {script_name} or {exe_name if exe_name else ''}")

def create_log_file():
    try:
        with open("uninstall_log.txt", "w") as f:
            f.write("ImageToMaple Uninstall Log\n")
            f.write("=" * 30 + "\n")
            f.write(microstatus_label.get("1.0", tk.END))
        update_microstatus("Log file created: uninstall_log.txt", 100)
        SCRIPT_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        print(SCRIPT_DIR)
        files.open_file(str(SCRIPT_DIR / "uninstall_log.txt"))
        root.destroy()
    except Exception as e:
        update_microstatus(f"Error creating log file: {e}", 100)

def create_uninstall_window():
    global root, progress, status_label, microstatus_label, left_frame
    root = tk.Tk()
    root.title("ImageToMaple Setup")
    root.resizable(False, False)
    root.attributes('-fullscreen', False)
    root.attributes('-topmost', True)
    root.update()
    root.attributes('-topmost', False)

    global icon_image
    icon_image = tk.PhotoImage(master=root, file=resource_path("ImageToMaple.png"))
    root.iconphoto(False, icon_image)
    
    window_width = 500
    window_height = 170
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = round((screen_height - window_height) // 2.2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    title_label = tk.Label(root, text="Uninstalling ImageToMaple", font=("Arial", 16), justify="center")
    title_label.pack(pady=(5, 5), anchor="n")
    
    left_frame = tk.Frame(root)
    left_frame.pack(side="left", fill="both", expand=True, padx=10)
    
    right_frame = tk.Frame(root)
    right_frame.pack(side="right", fill="both", expand=False, padx=(0, 10))
    
    status_label = tk.Label(left_frame, text="Initializing...", font=("Arial", 10), justify="center")
    status_label.pack( anchor="n")
    
    progress = ttk.Progressbar(left_frame, mode='indeterminate')
    progress.pack(pady=(10, 3), fill='x')
    progress.start()
    
    microstatus_frame = tk.Frame(right_frame)
    microstatus_frame.pack(fill="both", expand=True)
    
    microstatus_label_title = tk.Label(microstatus_frame, text="Details:", font=("Arial", 10))
    microstatus_label_title.pack(anchor="w")
    
    microstatus_label = tk.Text(microstatus_frame, font=("Arial", 8), width=35, height=5, wrap=tk.WORD)
    microstatus_label.pack(fill="x", expand=False)

def run_uninstall_process(root, exclude_current_process=True):
    global errored
    try:
        update_status("Starting uninstall process...", 1)
        time.sleep(1)
        
        script_filename = "ImageToMaple.py"
        executable_name = "ImageToMaple.exe"

        update_status("Killing running processes...")
        try:
            kill_running_script(script_filename, executable_name, exclude_current_pid=exclude_current_process)
            update_status("Process termination complete.", 30)
        except Exception as e:
            errored=True
            update_microstatus(f"Error during killing process: {e}")
            update_status("Process termination completed (with warnings).", 30)

        time.sleep(1)
        
        update_status("Removing shortcuts and files...")
        try:
            uninstall_using_startup_script()
            uninstall_using_scheduledtask()
            update_status("Files and shortcuts removed.",70)
        except Exception as e:
            errored=True
            update_microstatus(f"Error during removing target and config, log: {e}")
            update_status("File removal completed (with warnings).",70)
        
        time.sleep(1)

        progress.stop()
        progress.config(mode='determinate', value=100)
        update_microstatus("")
        
        button_frame = tk.Frame(left_frame)
        button_frame.pack(pady=(10, 5), anchor="n")
        
        tk.Button(button_frame, text="Ok", justify="center", width=10, command=root.destroy).pack(side="left", padx=(0, 5))
        tk.Button(button_frame, text="Create Log File", justify="center", width=12, command=create_log_file).pack(side="left", padx=(5, 0))
        if not errored:
            root.after(1000, update_status("Uninstall complete! Closing in 3..."))
            root.after(1000, update_status("Uninstall complete! Closing in 2..."))
            root.after(1000, update_status("Uninstall complete! Closing in 1..."))
            root.destroy()
        else:
            update_status("Uninstall complete! (With errors)")
        
    except Exception as e:
        progress.stop()
        update_status(f"Error during uninstall: {str(e)}")
        root.after(5000, root.destroy)

def uninstall_imagetomaple(exclude_current_process=False):
    global errored
    errored = False
    print(f"Starting ImageToMaple uninstall with GUI...")
    create_uninstall_window()
    root.after(1000, lambda: run_uninstall_process(root, exclude_current_process))
    root.mainloop()
    print("Uninstall complete.")

if __name__ == "__main__":
    # When run standalone, don't exclude current process
    uninstall_imagetomaple(exclude_current_process=False)