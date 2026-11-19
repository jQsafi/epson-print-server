"""Universal Python Backend for Epson Print & Scan Gateway (Flask Engine)."""

import os
import shutil
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

from .config import (
    FASTAPI_HOST,
    FASTAPI_PORT,
    LOCAL_IP,
    SPOOL_DIR,
    SCAN_DIR,
    PRINTED_OUTPUT_DIR,
    AIRPRINT_ENABLED,
    SIMULATION_MODE
)
from .scanner import list_scanners, acquire_scan
from .printer import list_printers, print_file, get_target_printer
from .airprint import AirPrintService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

app = Flask(__name__)

# Start AirPrint Service
airprint_service = AirPrintService() if AIRPRINT_ENABLED else None
if airprint_service:
    try:
        airprint_service.start()
    except Exception as e:
        logger.warning(f"AirPrint failed to start: {e}")


@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    response.headers['Access-Control-Allow-Methods'] = '*'
    return response


@app.route("/api/status", methods=["GET"])
def get_system_status():
    """Returns local network details, printer, and scanner info."""
    printers = list_printers()
    scanners = list_scanners()
    target_pr = get_target_printer()

    return jsonify({
        "status": "online",
        "simulation_mode": SIMULATION_MODE,
        "host_ip": LOCAL_IP,
        "default_printer": target_pr,
        "printers_count": len(printers),
        "scanners_count": len(scanners),
        "airprint_active": AIRPRINT_ENABLED
    })


@app.route("/api/printers", methods=["GET"])
def get_printers():
    """Lists all available printers with real-time status."""
    return jsonify({"printers": list_printers()})


@app.route("/api/scanners", methods=["GET"])
def get_scanners():
    """Lists all connected/simulated scanners."""
    return jsonify({"scanners": list_scanners()})


@app.route("/api/print", methods=["POST"])
def submit_print_job():
    """Accepts document/image upload and prints or spools to simulated PDF printer."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    copies = int(request.form.get("copies", 1))
    printer_name = request.form.get("printer", None)

    temp_file = SPOOL_DIR / uploaded_file.filename
    uploaded_file.save(str(temp_file))

    try:
        result = print_file(
            filepath=str(temp_file),
            printer_name=printer_name,
            copies=copies
        )
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        logger.error(f"Print job failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan", methods=["POST"])
def trigger_scan():
    """Triggers flatbed scan (or simulated scan) and returns file metadata."""
    dpi = int(request.args.get("dpi", 300))
    color_mode = request.args.get("color_mode", "color")
    file_format = request.args.get("format", "pdf")
    scanner_id = request.args.get("scanner_id", None)

    try:
        scan_result = acquire_scan(
            dpi=dpi,
            color_mode=color_mode,
            format=file_format,
            scanner_id=scanner_id
        )
        scan_result["download_url"] = f"/api/downloads/{scan_result['filename']}"
        return jsonify(scan_result)
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/downloads/<filename>", methods=["GET"])
def download_file(filename):
    """Serves scanned output files or spooled documents."""
    if (SCAN_DIR / filename).exists():
        return send_from_directory(str(SCAN_DIR), filename, as_attachment=False)
    elif (PRINTED_OUTPUT_DIR / filename).exists():
        return send_from_directory(str(PRINTED_OUTPUT_DIR), filename, as_attachment=False)
    elif (SPOOL_DIR / filename).exists():
        return send_from_directory(str(SPOOL_DIR), filename, as_attachment=False)
    return jsonify({"error": "File not found"}), 404


@app.route("/api/printed_outputs", methods=["GET"])
def list_printed_outputs():
    """Lists files produced by the simulated PDF printer."""
    files = []
    for f in sorted(PRINTED_OUTPUT_DIR.glob("*"), key=os.path.getmtime, reverse=True):
        files.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "download_url": f"/api/downloads/{f.name}"
        })
    return jsonify({"printed_jobs": files})


if __name__ == "__main__":
    logger.info(f"Starting Python Hardware Engine on {FASTAPI_HOST}:{FASTAPI_PORT}")
    app.run(host=FASTAPI_HOST, port=FASTAPI_PORT, debug=False)
