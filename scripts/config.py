import json
import logging
from pathlib import Path
import sys

SCRIPT_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config.json"

def load_config(CONFIG_PATH : Path) -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            logging.exception("Failed to load existing config, using defaults.")
            return {}
    logging.debug("Config file does not exist, using defaults.")
    return {}

def save_config(CONFIG_PATH, cfg: dict):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        logging.info(f"Config saved to {CONFIG_PATH}")
        logging.debug(f"Config content: {json.dumps(cfg, indent=2)}")
    except Exception:
        logging.exception(f"Failed to save config to {CONFIG_PATH}")

def append_config(CONFIG_PATH, cfg: dict):
    try:
        current_cfg = load_config(CONFIG_PATH)
        current_cfg.update(cfg)
        save_config(CONFIG_PATH, current_cfg)
        logging.info("Appended to config.")
    except Exception:
        logging.exception("Failed to append config.")