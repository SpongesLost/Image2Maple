import os
import psutil
from win32com.client import Dispatch
import subprocess

def uninstall_using_scheduledtask(task_name="ImageToMapleStartup"):
    try:
        print("Looking for scheduledtask...")
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name],
            capture_output=True,
            text=True
        )
        if "ERROR" not in result.stdout and "ERROR" not in result.stderr:
            print(f"Found scheduled task: {task_name}")
            result = subprocess.run(
                f'schtasks /query /tn "{task_name}" /v /fo LIST | find "Task To Run:"',
                shell=True,
                capture_output=True,
                text=True
            )
            path_to_application = result.stdout.replace("Task To Run:","").strip().strip('\"')
            print(f"Task points to: '{path_to_application}'")
            subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], check=True)
            try:
                if os.path.exists(path_to_application):
                    remove_target_file_config_and_log(path_to_application)
                else:
                    print(f"Scheduled task does not point to existing path {path_to_application}")
            except Exception as e:
                print(f"Error during killing process: {e}")
        else:
            print(f"No scheduled task named {task_name} found.")
            
    except Exception as e:
        print(f"Error removing scheduled task {task_name}: {e}")

def remove_target_file_config_and_log(path):
    try:
        target_dir = os.path.dirname(path)
        config_path = os.path.join(target_dir, "config.json")
        if os.path.exists(config_path):
            os.remove(config_path)
            print(f"Deleted config file: {config_path}")
        else:
            print(f"No config.json found at {config_path}")
        log_path = os.path.join(target_dir, "latex_to_maple.log")
        if os.path.exists(log_path):
            os.remove(log_path)
            print(f"Deleted log file: {log_path}")
        else:
            print(f"No latex_to_maple.log found at {log_path}")
        os.remove(path)
        print(f"Deleted target script file: {path}")
    except Exception as e:
        print(f"Failed to delete target, config or log file: {e}")

def uninstall_using_startup_script():
    startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
    shortcut_path = os.path.join(startup_dir, "ImageToMaple.lnk")

    if os.path.exists(shortcut_path):
        print("Removing depricated startup script and target files...")
        try:
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortcut(shortcut_path)
            target_path = shortcut.TargetPath   # usually python.exe
            arguments = shortcut.Arguments      # usually the script path
            print(f"Found startup shortcut: {shortcut_path}")
            print(f"Shortcut points to: {target_path}")
            print(f"Shortcut arguments: {arguments}")
            
            os.remove(shortcut_path)
            print(f"Deleted startup shortcut: {shortcut_path}")
            if arguments:
                script_path = arguments.strip('"')
                if os.path.exists(script_path) and os.path.isfile(script_path):
                    remove_target_file_config_and_log(script_path)
                else:
                    print(f"Target script file does not exist or is not a file: {script_path}")
            else:
                print("No arguments found in shortcut to delete.")
                if "ImageToMaple" in target_path:
                    print(f"Identified 'ImageToMaple' in target path: {target_path}")
                    if os.path.exists(target_path) and os.path.isfile(target_path):
                        remove_target_file_config_and_log(target_path)
            return True
        except Exception as e:
            print(f"Error handling shortcut: {e}")
            return False
    else:
        print("Depricated startup shortcut not found.")
        return False

def kill_process_and_children(proc):
    try:
        children = proc.children(recursive=True)
        for child in children:
            print(f"Terminating child process {child.pid}")
            child.terminate()
        proc.terminate()
        proc.wait(timeout=5)
    except psutil.TimeoutExpired:
        print(f"Process {proc.pid} did not terminate, killing now")
        proc.kill()
    except Exception as e:
        print(f"Error killing process {proc.pid}: {e}")

def kill_running_script(script_name, exe_name=None):
    found = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            proc_name = proc.info['name'].lower() if proc.info['name'] else ''
            cmdline = proc.info['cmdline'] or []

            if 'python' in proc_name:
                # Check if any argument matches the script filename exactly (case-insensitive)
                if any(os.path.basename(arg).lower() == script_name.lower() for arg in cmdline):
                    print(f"Killing python process {proc.pid} running {script_name}")
                    kill_process_and_children(proc)
                    found = True
            elif exe_name and proc_name == exe_name.lower():
                print(f"Killing executable process {proc.pid} named {exe_name}")
                kill_process_and_children(proc)
                found = True
        except psutil.NoSuchProcess:
            pass
        except psutil.AccessDenied:
            print(f"Access denied to process {proc.pid}")
        except Exception as e:
            print(f"Unexpected error with process {proc.pid}: {e}")

    if not found:
        print(f"No running process found for {script_name} or {exe_name if exe_name else ''}")

if __name__ == "__main__":
    print("Starting uninstall process...")
    script_filename = "ImageToMaple.py"
    executable_name = "ImageToMaple.exe"

    try:
        print("Killing running script/executable...")
        kill_running_script(script_filename, executable_name)
        print("Process killing done.")
    except Exception as e:
        print(f"Error during killing process: {e}")

    try:
        uninstall_using_startup_script()
        uninstall_using_scheduledtask()
        print("Shortcut and target files removed.")
    except Exception as e:
        print(f"Error during removing target and config, log: {e}")

    try:
        input("\nUninstall complete. Press Enter to exit...")
    except (EOFError, RuntimeError):
        print("Uninstall complete.")
        import time
        time.sleep(2)