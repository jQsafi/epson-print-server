"""Windows Image Acquisition (WIA 2.0) Scanner Controller with Simulation Support."""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw

from .config import SCAN_DIR, DEFAULT_SCANNER_KEYWORD, IS_WINDOWS, SIMULATION_MODE

logger = logging.getLogger("scanner")

# WIA Constants
WIA_DEVICE_TYPE_SCANNER = 1
WIA_IPS_CUR_INTENT = 6146       # 1=Color, 2=Grayscale, 4=B&W
WIA_IPS_XRES = 6147             # Horizontal resolution (DPI)
WIA_IPS_YRES = 6148             # Vertical resolution (DPI)

INTENT_MAP = {
    "color": 1,
    "grayscale": 2,
    "bw": 4
}


def generate_simulated_scan(dpi: int = 300, color_mode: str = "color") -> Image.Image:
    """Generates a realistic test scan document with calibration patterns and metadata."""
    # A4 standard at given DPI: ~8.27 x 11.69 inches
    # For fast simulation, use proportional canvas
    width = int(8.27 * dpi / 2)
    height = int(11.69 * dpi / 2)

    bg_color = (255, 255, 255) if color_mode != "bw" else 255
    mode = "RGB" if color_mode != "bw" else "1"
    img = Image.new(mode, (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(100, 100, 100) if mode == "RGB" else 0, width=3)

    # Header
    draw.rectangle([(40, 40), (width - 40, 120)], fill=(37, 99, 235) if mode == "RGB" else 0)
    draw.text((60, 65), "EPSON ECOTANK L3110 - SIMULATED SCAN", fill=(255, 255, 255) if mode == "RGB" else 1)

    # Scan Metadata
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    info_text = f"Mode: {color_mode.upper()} | DPI: {dpi} | Acquired: {timestamp_str}"
    draw.text((60, 150), info_text, fill=(50, 50, 50) if mode == "RGB" else 0)

    # Color Calibration Bars (if color)
    if color_mode == "color":
        colors = [(239, 68, 68), (245, 158, 11), (16, 185, 129), (59, 130, 246), (139, 92, 246), (30, 41, 59)]
        bar_w = (width - 120) // len(colors)
        for idx, col in enumerate(colors):
            x0 = 60 + idx * bar_w
            draw.rectangle([(x0, 200), (x0 + bar_w - 5, 260)], fill=col)

    # Simulated Document Text
    draw.text((60, 300), "This is a verified test scan produced by the Epson All-in-One Gateway.", fill=(30, 30, 30) if mode == "RGB" else 0)
    draw.text((60, 340), "Simulated hardware interface: Ready and functional.", fill=(80, 80, 80) if mode == "RGB" else 0)

    if color_mode == "grayscale":
        img = img.convert("L")
    elif color_mode == "bw":
        img = img.convert("1")

    return img


def list_scanners() -> List[Dict[str, Any]]:
    """Enumerate scanners (Windows WIA or Simulated Scanner)."""
    if not IS_WINDOWS or SIMULATION_MODE:
        return [{
            "id": "simulated-wia-scanner",
            "name": "EPSON L3110 Series Scanner (Simulated)",
            "description": "Virtual WIA 2.0 Flatbed Scanner",
            "is_epson": True
        }]

    scanners = []
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()

        device_manager = win32com.client.Dispatch("WIA.DeviceManager")
        for info in device_manager.DeviceInfos:
            if info.Type == WIA_DEVICE_TYPE_SCANNER:
                scanners.append({
                    "id": info.DeviceID,
                    "name": str(info.Properties("Name").Value),
                    "description": str(info.Properties("Description").Value) if "Description" in [p.Name for p in info.Properties] else "",
                    "is_epson": DEFAULT_SCANNER_KEYWORD.lower() in str(info.Properties("Name").Value).lower()
                })
    except Exception as e:
        logger.error(f"Error listing WIA scanners: {e}")
        scanners.append({
            "id": "simulated-wia-scanner",
            "name": "EPSON L3110 Series Scanner (Fallback)",
            "description": "Virtual WIA Scanner",
            "is_epson": True
        })
    return scanners


def acquire_scan(
    dpi: int = 300,
    color_mode: str = "color",
    format: str = "pdf",
    scanner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Triggers flatbed scan (via native WIA 2.0 COM on Windows or via simulated scanner engine).
    Outputs to JPEG/PNG or PDF.
    """
    timestamp = int(time.time())
    final_output_path = SCAN_DIR / f"scan_{timestamp}.{format.lower()}"

    # 1. Simulation Engine (Linux/Android or simulated testing)
    if not IS_WINDOWS or SIMULATION_MODE:
        logger.info(f"[SIMULATOR] Generating simulated scan: DPI={dpi}, Mode={color_mode}, Format={format}")
        sim_img = generate_simulated_scan(dpi=dpi, color_mode=color_mode)

        if format.lower() == "pdf":
            # Convert to RGB before saving as PDF
            sim_img.convert("RGB").save(str(final_output_path), "PDF", resolution=dpi)
        elif format.lower() == "png":
            sim_img.save(str(final_output_path), "PNG")
        else:
            sim_img.convert("RGB").save(str(final_output_path), "JPEG", quality=90)

        return {
            "success": True,
            "filename": final_output_path.name,
            "filepath": str(final_output_path),
            "format": format.lower(),
            "dpi": dpi,
            "color_mode": color_mode,
            "size_bytes": final_output_path.stat().st_size,
            "engine": "simulated_wia_engine"
        }

    # 2. Windows 11 Native WIA 2.0 COM
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    raw_temp_path = SCAN_DIR / f"raw_scan_{timestamp}.bmp"

    try:
        device_manager = win32com.client.Dispatch("WIA.DeviceManager")
        selected_device = None

        for info in device_manager.DeviceInfos:
            if info.Type == WIA_DEVICE_TYPE_SCANNER:
                dev_name = str(info.Properties("Name").Value)
                if scanner_id and info.DeviceID == scanner_id:
                    selected_device = info.Connect()
                    break
                elif not scanner_id and DEFAULT_SCANNER_KEYWORD.lower() in dev_name.lower():
                    selected_device = info.Connect()
                    break
                elif not selected_device:
                    selected_device = info.Connect()

        if not selected_device:
            raise RuntimeError("No WIA scanner device found. Ensure the Epson scanner USB is connected and powered on.")

        item = selected_device.Items[1]

        try:
            intent_val = INTENT_MAP.get(color_mode.lower(), 1)
            item.Properties(str(WIA_IPS_CUR_INTENT)).Value = intent_val
            item.Properties(str(WIA_IPS_XRES)).Value = int(dpi)
            item.Properties(str(WIA_IPS_YRES)).Value = int(dpi)
        except Exception as prop_err:
            logger.warning(f"Could not set custom WIA properties: {prop_err}. Using scanner defaults.")

        dialog = win32com.client.Dispatch("WIA.CommonDialog")
        image_file = dialog.ShowTransfer(item, "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}", False)

        if not image_file:
            raise RuntimeError("Scan was cancelled or failed to produce image data.")

        if raw_temp_path.exists():
            raw_temp_path.unlink()
        image_file.SaveFile(str(raw_temp_path))

        with Image.open(str(raw_temp_path)) as img:
            rgb_img = img.convert("RGB") if color_mode != "bw" else img.convert("1")
            if format.lower() == "pdf":
                rgb_img.save(str(final_output_path), "PDF", resolution=dpi)
            elif format.lower() == "png":
                img.save(str(final_output_path), "PNG")
            else:
                rgb_img.save(str(final_output_path), "JPEG", quality=90)

        if raw_temp_path.exists():
            raw_temp_path.unlink()

        return {
            "success": True,
            "filename": final_output_path.name,
            "filepath": str(final_output_path),
            "format": format.lower(),
            "dpi": dpi,
            "color_mode": color_mode,
            "size_bytes": final_output_path.stat().st_size,
            "engine": "windows_wia_com"
        }

    except Exception as e:
        logger.error(f"Scan acquisition failed: {e}")
        if raw_temp_path.exists():
            raw_temp_path.unlink()
        raise e
    finally:
        pythoncom.CoUninitialize()
