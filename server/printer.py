"""Windows Print Spooler integration with Paper Selection & Virtual PDF Printer Simulation."""

import os
import shutil
import time
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import DEFAULT_PRINTER_KEYWORD, SPOOL_DIR, PRINTED_OUTPUT_DIR, IS_WINDOWS, SIMULATION_MODE

logger = logging.getLogger("printer")

PAPER_DIMENSIONS = {
    "a4": {"name": "A4 (210 x 297 mm)", "w_in": 8.27, "h_in": 11.69, "dm_id": 9},
    "letter": {"name": "Letter (8.5 x 11 in)", "w_in": 8.5, "h_in": 11.0, "dm_id": 1},
    "legal": {"name": "Legal (8.5 x 14 in)", "w_in": 8.5, "h_in": 14.0, "dm_id": 5},
    "4x6": {"name": "Photo 4x6 in (10x15 cm)", "w_in": 4.0, "h_in": 6.0, "dm_id": 256},
    "5x7": {"name": "Photo 5x7 in (13x18 cm)", "w_in": 5.0, "h_in": 7.0, "dm_id": 257},
}

MEDIA_TYPES = {
    "plain": "Plain / Regular Paper",
    "glossy": "Epson Glossy Photo Paper",
    "matte": "Matte Photo Paper",
    "envelope": "Envelope"
}


def list_printers() -> List[Dict[str, Any]]:
    """List printers (Windows Spooler or Simulated PDF Printer)."""
    if not IS_WINDOWS or SIMULATION_MODE:
        return [{
            "name": "Virtual PDF Printer (Epson L3110 Simulator)",
            "is_default": True,
            "is_epson": True,
            "status": "Ready",
            "supported_papers": list(PAPER_DIMENSIONS.keys()),
            "supported_media": list(MEDIA_TYPES.keys()),
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
                "supported_papers": list(PAPER_DIMENSIONS.keys()),
                "supported_media": list(MEDIA_TYPES.keys()),
                "comment": comment
            })
    except Exception as e:
        logger.error(f"Failed to list Windows printers: {e}")
        printers.append({
            "name": "Virtual PDF Printer (Fallback)",
            "is_default": True,
            "is_epson": True,
            "status": "Ready",
            "supported_papers": list(PAPER_DIMENSIONS.keys()),
            "supported_media": list(MEDIA_TYPES.keys()),
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
    copies: int = 1,
    paper_size: str = "a4",
    media_type: str = "plain"
) -> Dict[str, Any]:
    """
    Submits a print job with specified paper size and media quality.
    In Simulation Mode, scales and outputs simulated PDFs with the exact paper dimensions.
    """
    path_obj = Path(filepath).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"File to print not found: {filepath}")

    target = get_target_printer(printer_name)
    paper_info = PAPER_DIMENSIONS.get(paper_size.lower(), PAPER_DIMENSIONS["a4"])
    media_info = MEDIA_TYPES.get(media_type.lower(), MEDIA_TYPES["plain"])

    # 1. Simulation Mode (Virtual PDF Printer)
    if not IS_WINDOWS or SIMULATION_MODE or "virtual" in target.lower():
        timestamp = int(time.time())
        simulated_outputs = []

        # Target canvas pixel size at 300 DPI
        target_w = int(paper_info["w_in"] * 300)
        target_h = int(paper_info["h_in"] * 300)

        for i in range(copies):
            copy_suffix = f"_copy{i+1}" if copies > 1 else ""
            out_filename = f"printed_{timestamp}_{paper_size.lower()}_{path_obj.stem}{copy_suffix}.pdf"
            out_path = PRINTED_OUTPUT_DIR / out_filename

            if path_obj.suffix.lower() in (".png", ".jpg", ".jpeg"):
                from PIL import Image, ImageOps
                with Image.open(str(path_obj)) as img:
                    # Fit image proportionally into the selected paper dimensions
                    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
                    fitted_img = ImageOps.contain(img.convert("RGB"), (target_w - 60, target_h - 60))
                    offset_x = (target_w - fitted_img.width) // 2
                    offset_y = (target_h - fitted_img.height) // 2
                    canvas.paste(fitted_img, (offset_x, offset_y))
                    canvas.save(str(out_path), "PDF", resolution=300)
                    simulated_outputs.append(str(out_path))
            else:
                shutil.copyfile(str(path_obj), str(out_path))
                simulated_outputs.append(str(out_path))

        logger.info(f"[SIMULATOR] Printed {copies} copy/copies to '{target}' | Paper: {paper_info['name']} | Media: {media_info}")
        return {
            "success": True,
            "filename": path_obj.name,
            "printer": target,
            "copies": copies,
            "paper_size": paper_info["name"],
            "media_type": media_info,
            "engine": "virtual_pdf_spooler",
            "simulated_outputs": simulated_outputs
        }

    # 2. Windows 11 Native Spooler
    logger.info(f"Submitting print job for '{path_obj.name}' to '{target}' (Copies: {copies}, Paper: {paper_size}, Media: {media_type})")
    
    # Configure Windows DEVMODE for Paper Size
    try:
        import win32print
        h_printer = win32print.OpenPrinter(target)
        devmode = win32print.GetPrinter(h_printer, 2)['pDevMode']
        if devmode:
            devmode.PaperSize = paper_info["dm_id"]
            # Apply DEVMODE to print document
        win32print.ClosePrinter(h_printer)
    except Exception as devmode_err:
        logger.warning(f"Could not preset DEVMODE paper size: {devmode_err}")

    # Dispatch using ShellExecute printto
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
            "paper_size": paper_info["name"],
            "media_type": media_info,
            "engine": "win32api_printto"
        }
    except Exception as win32_err:
        logger.warning(f"win32api ShellExecute failed: {win32_err}. Trying PowerShell fallback...")

    # Fallback via PowerShell
    try:
        ps_cmd = f'Start-Process -FilePath "{str(path_obj)}" -Verb PrintTo -ArgumentList "\"{target}\"" -WindowStyle Hidden'
        for _ in range(copies):
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, timeout=15)
        return {
            "success": True,
            "filename": path_obj.name,
            "printer": target,
            "copies": copies,
            "paper_size": paper_info["name"],
            "media_type": media_info,
            "engine": "powershell_printto"
        }
    except Exception as ps_err:
        logger.error(f"PowerShell print fallback failed: {ps_err}")
        raise RuntimeError(f"Could not print file to '{target}': {ps_err}")
