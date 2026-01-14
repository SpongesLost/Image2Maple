import json
import logging
from pathlib import Path

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
        logging.info("Config saved.")
    except Exception:
        logging.exception("Failed to save config.")