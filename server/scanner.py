"""Windows Image Acquisition (WIA 2.0) Scanner Controller for Epson Multifunction."""

import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

from .config import SCAN_DIR, DEFAULT_SCANNER_KEYWORD

logger = logging.getLogger("scanner")

# WIA Constants
WIA_DEVICE_TYPE_SCANNER = 1

# WIA Item Property IDs
WIA_IPS_CUR_INTENT = 6146       # 1=Color, 2=Grayscale, 4=B&W
WIA_IPS_XRES = 6147             # Horizontal resolution (DPI)
WIA_IPS_YRES = 6148             # Vertical resolution (DPI)

INTENT_MAP = {
    "color": 1,
    "grayscale": 2,
    "bw": 4
}


def list_scanners() -> List[Dict[str, Any]]:
    """Enumerate all connected WIA scanners on Windows."""
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
    return scanners


def acquire_scan(
    dpi: int = 300,
    color_mode: str = "color",
    format: str = "pdf",
    scanner_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Triggers flatbed scan on the connected Epson scanner via WIA 2.0 COM.
    Converts and saves the output to JPEG/PNG or PDF.
    """
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    timestamp = int(time.time())
    raw_temp_path = SCAN_DIR / f"raw_scan_{timestamp}.bmp"
    final_output_path = SCAN_DIR / f"scan_{timestamp}.{format.lower()}"

    try:
        device_manager = win32com.client.Dispatch("WIA.DeviceManager")
        selected_device = None

        # Locate target scanner
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

        # Access default scan item (flatbed)
        item = selected_device.Items[1]

        # Apply scan settings (Resolution & Color Intent)
        try:
            intent_val = INTENT_MAP.get(color_mode.lower(), 1)
            item.Properties(str(WIA_IPS_CUR_INTENT)).Value = intent_val
            item.Properties(str(WIA_IPS_XRES)).Value = int(dpi)
            item.Properties(str(WIA_IPS_YRES)).Value = int(dpi)
        except Exception as prop_err:
            logger.warning(f"Could not set custom WIA properties: {prop_err}. Using scanner defaults.")

        # Execute Transfer
        dialog = win32com.client.Dispatch("WIA.CommonDialog")
        # Format ID for BMP: {B96B3CAB-0728-11D3-9D7B-0000F81EF32E}
        image_file = dialog.ShowTransfer(item, "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}", False)

        if not image_file:
            raise RuntimeError("Scan was cancelled or failed to produce image data.")

        # Save raw transfer
        if raw_temp_path.exists():
            raw_temp_path.unlink()
        image_file.SaveFile(str(raw_temp_path))

        # Convert using Pillow to final format
        with Image.open(str(raw_temp_path)) as img:
            rgb_img = img.convert("RGB") if color_mode != "bw" else img.convert("1")
            
            if format.lower() == "pdf":
                rgb_img.save(str(final_output_path), "PDF", resolution=dpi)
            elif format.lower() == "png":
                img.save(str(final_output_path), "PNG")
            else:
                rgb_img.save(str(final_output_path), "JPEG", quality=90)

        # Cleanup raw BMP
        if raw_temp_path.exists():
            raw_temp_path.unlink()

        return {
            "success": True,
            "filename": final_output_path.name,
            "filepath": str(final_output_path),
            "format": format.lower(),
            "dpi": dpi,
            "color_mode": color_mode,
            "size_bytes": final_output_path.stat().st_size
        }

    except Exception as e:
        logger.error(f"Scan acquisition failed: {e}")
        if raw_temp_path.exists():
            raw_temp_path.unlink()
        raise e
    finally:
        pythoncom.CoUninitialize()
