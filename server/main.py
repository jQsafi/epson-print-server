"""FastAPI Backend for Epson L3110 All-in-One Print & Scan Server."""

import os
import shutil
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import (
    FASTAPI_HOST,
    FASTAPI_PORT,
    LOCAL_IP,
    SPOOL_DIR,
    SCAN_DIR,
    AIRPRINT_ENABLED
)
from .scanner import list_scanners, acquire_scan
from .printer import list_printers, print_file, get_target_printer
from .airprint import AirPrintService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

airprint_service = AirPrintService() if AIRPRINT_ENABLED else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting Epson Print & Scan Server on {LOCAL_IP}:{FASTAPI_PORT}")
    if airprint_service:
        try:
            airprint_service.start()
        except Exception as e:
            logger.warning(f"AirPrint service failed to start: {e}")
    yield
    # Shutdown
    if airprint_service:
        airprint_service.stop()
    logger.info("Server stopped.")


app = FastAPI(
    title="Epson L3110 Print & Scan Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# Allow Cross-Origin Requests from Node.js Web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
async def get_system_status():
    """Returns local network details, active printer, and scanner info."""
    printers = list_printers()
    scanners = list_scanners()
    target_pr = get_target_printer()

    return {
        "status": "online",
        "host_ip": LOCAL_IP,
        "default_printer": target_pr,
        "printers_count": len(printers),
        "scanners_count": len(scanners),
        "airprint_active": AIRPRINT_ENABLED
    }


@app.get("/api/printers")
async def get_printers():
    """Lists all available printers with real-time status."""
    return {"printers": list_printers()}


@app.get("/api/scanners")
async def get_scanners():
    """Lists all connected WIA scanners."""
    return {"scanners": list_scanners()}


@app.post("/api/print")
async def submit_print_job(
    file: UploadFile = File(...),
    copies: int = Form(1),
    printer: str = Form(None)
):
    """
    Accepts a document/image upload and submits it to the Windows Print Spooler.
    """
    try:
        temp_file = SPOOL_DIR / file.filename
        with temp_file.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = print_file(
            filepath=str(temp_file),
            printer_name=printer,
            copies=copies
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Print job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan")
async def trigger_scan(
    dpi: int = Query(300, enum=[150, 300, 600]),
    color_mode: str = Query("color", enum=["color", "grayscale", "bw"]),
    format: str = Query("pdf", enum=["pdf", "jpg", "png"]),
    scanner_id: str = Query(None)
):
    """
    Triggers flatbed scan on the Epson scanner and returns the file metadata.
    """
    try:
        scan_result = acquire_scan(
            dpi=dpi,
            color_mode=color_mode,
            format=format,
            scanner_id=scanner_id
        )
        download_url = f"/api/downloads/{scan_result['filename']}"
        scan_result["download_url"] = download_url
        return scan_result
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/downloads/{filename}")
async def download_file(filename: str):
    """Serves scanned output files or spooled documents."""
    file_path = SCAN_DIR / filename
    if not file_path.exists():
        file_path = SPOOL_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = "application/pdf" if filename.endswith(".pdf") else "image/jpeg"
    return FileResponse(path=file_path, filename=filename, media_type=media_type)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host=FASTAPI_HOST, port=FASTAPI_PORT, reload=True)
