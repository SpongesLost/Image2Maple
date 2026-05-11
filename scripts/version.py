import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_version() -> str:
    try:
        with open(resource_path(".VERSION")) as f:
            return f.readline()[:-1]
    except ImportError:
        return "dev"

__version__ = get_version()

if __name__ == "__main__":
    print(__version__)
    input()