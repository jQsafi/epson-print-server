"""Windows Print Spooler integration with Virtual PDF Printer Simulation."""

import os
import shutil
import time
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DEFAULT_PRINTER_KEYWORD, SPOOL_DIR, PRINTED_OUTPUT_DIR, IS_WINDOWS, SIMULATION_MODE

logger = logging.getLogger("printer")


def list_printers() -> List[Dict[str, Any]]:
    """List printers (Windows Spooler or Simulated PDF Printer)."""
    if not IS_WINDOWS or SIMULATION_MODE:
        return [{
            "name": "Virtual PDF Printer (Epson L3110 Simulator)",
            "is_default": True,
            "is_epson": True,
            "status": "Ready",
            "comment": "Simulated PDF Spooler - saves printed jobs as PDF to temp/printed_output/"
        }]

    printers = []
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        installed = win32print.EnumPrinters(flags)
        default_printer = win32print.GetDefaultPrinter()

        for flags, description, name, comment in installed:
            is_epson = DEFAULT_PRINTER_KEYWORD.lower() in name.lower()
            is_default = (name == default_printer)
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
        printers.append({
            "name": "Virtual PDF Printer (Fallback)",
            "is_default": True,
            "is_epson": True,
            "status": "Ready",
            "comment": "Fallback Virtual PDF Printer"
        })
    return printers


def get_target_printer(printer_name: Optional[str] = None) -> str:
    """Finds target printer name."""
    if not IS_WINDOWS or SIMULATION_MODE:
        return "Virtual PDF Printer (Epson L3110 Simulator)"

    try:
        import win32print
        all_printers = list_printers()
        if printer_name:
            for p in all_printers:
                if p["name"].lower() == printer_name.lower():
                    return p["name"]

        for p in all_printers:
            if p.get("is_epson"):
                return p["name"]

        return win32print.GetDefaultPrinter()
    except Exception as e:
        logger.warning(f"Using fallback printer selection: {e}")
        return printer_name or "Virtual PDF Printer (Epson L3110 Simulator)"


def print_file(
    filepath: str,
    printer_name: Optional[str] = None,
    copies: int = 1
) -> Dict[str, Any]:
    """
    Prints a file.
    In Simulation Mode (or non-Windows), acts as a Virtual PDF Printer:
    spools, stores, and outputs simulated printed PDF files into temp/printed_output/.
    """
    path_obj = Path(filepath).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"File to print not found: {filepath}")

    target = get_target_printer(printer_name)

    # 1. Simulation Mode (Virtual PDF Printer)
    if not IS_WINDOWS or SIMULATION_MODE or "virtual" in target.lower():
        timestamp = int(time.time())
        simulated_outputs = []

        for i in range(copies):
            copy_suffix = f"_copy{i+1}" if copies > 1 else ""
            out_filename = f"printed_{timestamp}_{path_obj.stem}{copy_suffix}{path_obj.suffix}"
            out_path = PRINTED_OUTPUT_DIR / out_filename

            # If it's an image, we can also convert to PDF or copy directly
            if path_obj.suffix.lower() in (".png", ".jpg", ".jpeg"):
                from PIL import Image
                with Image.open(str(path_obj)) as img:
                    pdf_out = PRINTED_OUTPUT_DIR / f"printed_{timestamp}_{path_obj.stem}{copy_suffix}.pdf"
                    img.convert("RGB").save(str(pdf_out), "PDF")
                    simulated_outputs.append(str(pdf_out))
            else:
                shutil.copyfile(str(path_obj), str(out_path))
                simulated_outputs.append(str(out_path))

        logger.info(f"[SIMULATOR] Printed {copies} copy/copies of '{path_obj.name}' to '{target}'. Output: {simulated_outputs}")
        return {
            "success": True,
            "filename": path_obj.name,
            "printer": target,
            "copies": copies,
            "engine": "virtual_pdf_spooler",
            "simulated_outputs": simulated_outputs
        }

    # 2. Windows 11 Native Spooler
    logger.info(f"Submitting print job for '{path_obj.name}' to '{target}' (Copies: {copies})")
    try:
        import win32api
        for _ in range(copies):
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

    # Strategy 2: PowerShell Start-Process
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
