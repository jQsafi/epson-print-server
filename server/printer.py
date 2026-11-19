"""Windows Print Spooler integration for Epson L3110."""

import os
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DEFAULT_PRINTER_KEYWORD, SPOOL_DIR

logger = logging.getLogger("printer")


def list_printers() -> List[Dict[str, Any]]:
    """List all installed Windows printers using win32print."""
    printers = []
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        installed = win32print.EnumPrinters(flags)
        default_printer = win32print.GetDefaultPrinter()

        for flags, description, name, comment in installed:
            is_epson = DEFAULT_PRINTER_KEYWORD.lower() in name.lower()
            is_default = (name == default_printer)

            # Query detailed status
            status_str = "Ready"
            try:
                h_printer = win32print.OpenPrinter(name)
                info = win32print.GetPrinter(h_printer, 2)
                status_code = info['Status']
                win32print.ClosePrinter(h_printer)

                if status_code & win32print.PRINTER_STATUS_OFFLINE:
                    status_str = "Offline"
                elif status_code & win32print.PRINTER_STATUS_PAPER_JAM:
                    status_str = "Paper Jam"
                elif status_code & win32print.PRINTER_STATUS_PAPER_OUT:
                    status_str = "Out of Paper"
                elif status_code & win32print.PRINTER_STATUS_BUSY:
                    status_str = "Busy"
            except Exception:
                pass

            printers.append({
                "name": name,
                "is_default": is_default,
                "is_epson": is_epson,
                "status": status_str,
                "comment": comment
            })
    except Exception as e:
        logger.error(f"Failed to list Windows printers: {e}")
    return printers


def get_target_printer(printer_name: Optional[str] = None) -> str:
    """Finds the designated Epson printer or falls back to system default."""
    try:
        import win32print
        all_printers = list_printers()

        if printer_name:
            for p in all_printers:
                if p["name"].lower() == printer_name.lower():
                    return p["name"]

        # Search for Epson keyword
        for p in all_printers:
            if p["is_epson"]:
                return p["name"]

        # Default fallback
        return win32print.GetDefaultPrinter()
    except Exception as e:
        logger.warning(f"Using fallback printer selection: {e}")
        return printer_name or "EPSON L3110 Series"


def print_file(
    filepath: str,
    printer_name: Optional[str] = None,
    copies: int = 1
) -> Dict[str, Any]:
    """
    Submits a file directly to the Windows Print Spooler for the target printer.
    Dispatches through win32api ShellExecute or PowerShell Start-Process.
    """
    target = get_target_printer(printer_name)
    path_obj = Path(filepath).resolve()

    if not path_obj.exists():
        raise FileNotFoundError(f"File to print not found: {filepath}")

    logger.info(f"Submitting print job for '{path_obj.name}' to '{target}' (Copies: {copies})")

    # Strategy 1: win32api ShellExecute "printto"
    try:
        import win32api
        for _ in range(copies):
            # 0 = SW_HIDE
            win32api.ShellExecute(
                0,
                "printto",
                str(path_obj),
                f'"{target}"',
                ".",
                0
            )
        return {
            "success": True,
            "filename": path_obj.name,
            "printer": target,
            "copies": copies,
            "engine": "win32api_printto"
        }
    except Exception as win32_err:
        logger.warning(f"win32api ShellExecute failed: {win32_err}. Trying PowerShell fallback...")

    # Strategy 2: PowerShell Start-Process with -Verb PrintTo
    try:
        ps_cmd = f'Start-Process -FilePath "{str(path_obj)}" -Verb PrintTo -ArgumentList "\"{target}\"" -WindowStyle Hidden'
        for _ in range(copies):
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, timeout=15)
        return {
            "success": True,
            "filename": path_obj.name,
            "printer": target,
            "copies": copies,
            "engine": "powershell_printto"
        }
    except Exception as ps_err:
        logger.error(f"PowerShell print fallback failed: {ps_err}")
        raise RuntimeError(f"Could not print file to '{target}': {ps_err}")
