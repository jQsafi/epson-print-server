"""Configuration settings for Epson Print & Scan Server (with Simulation Support)."""

import os
import platform
from pathlib import Path
import socket

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
SPOOL_DIR = BASE_DIR / "temp" / "spool"
SCAN_DIR = BASE_DIR / "temp" / "scans"
PRINTED_OUTPUT_DIR = BASE_DIR / "temp" / "printed_output"

SPOOL_DIR.mkdir(parents=True, exist_ok=True)
SCAN_DIR.mkdir(parents=True, exist_ok=True)
PRINTED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OS & Mode Detection
IS_WINDOWS = platform.system() == "Windows"
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", str(not IS_WINDOWS)).lower() in ("true", "1", "yes")

# Network & Ports
FASTAPI_HOST = "0.0.0.0"
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", 5000))
NODE_WEB_PORT = int(os.environ.get("PORT", 3000))
IPP_PORT = int(os.environ.get("IPP_PORT", 6310 if not IS_WINDOWS else 631))

# Printer & Scanner Filters
DEFAULT_PRINTER_KEYWORD = os.environ.get("PRINTER_KEYWORD", "L3110")
DEFAULT_SCANNER_KEYWORD = os.environ.get("SCANNER_KEYWORD", "L3110")

# AirPrint Defaults
AIRPRINT_ENABLED = os.environ.get("AIRPRINT_ENABLED", "true").lower() in ("true", "1", "yes")

def get_local_ip() -> str:
    """Detect the local machine IP address on the Wi-Fi/LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
