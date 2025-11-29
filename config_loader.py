# config_loader.py
import configparser

CONFIG_FILE = "configProcess.ini"

_cfg_cache = None   # Cached values (INI read only once)

def load_config():
    global _cfg_cache

    # Return cached config if already loaded
    if _cfg_cache is not None:
        return _cfg_cache

    cfg = configparser.ConfigParser()
    read_files = cfg.read(CONFIG_FILE)

    if not read_files:
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    if "PATHS" not in cfg:
        raise KeyError("Section [PATHS] missing in configProcess.ini")

    section = cfg["PATHS"]

    # Load everything once
    _cfg_cache = {
        "TARGET_DIRECTORY": section.get("TARGET_DIRECTORY", ".").strip().strip('"').strip("'"),
        "EQUITY_FILE_NAME": section.get("EQUITY_FILE_NAME", "").strip().strip('"').strip("'"),
        "DELIVERY_FILE_NAME": section.get("DELIVERY_FILE_NAME", "").strip().strip('"').strip("'"),
        "SD_MULTIPLIER": float(section.get("SD_MULTIPLIER", "0.2")),
        "TRADING_QTY": int(section.get("TRADING_QTY", "1000")),
        "INVESTMENT_AMOUNT": int(section.get("INVESTMENT_AMOUNT", "100000")),
        "DIFFERENCE_THRESHOLD_PCT": float(section.get("VWAP_EXPAND_PCT", "5.0")),
        "SYMBOL": section.get("SYMBOL", "STOCK")
    }

    return _cfg_cache
