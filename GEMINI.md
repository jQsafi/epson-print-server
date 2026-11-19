# Antigravity Instructions for Epson Print & Scan Server

This project is an All-in-One Print & Scan Server for the **Epson EcoTank L3110** hosted on **Windows 11** with a hybrid Python (Hardware) and Node.js (Web UI) architecture.

## Primary Invariants
1. **Zero C# / Zero .NET**: All Windows hardware automation uses native Win32 APIs via Python (`pywin32`) and WIA 2.0 COM (`win32com.client`).
2. **Safe COM Lifecycle**: Always call `pythoncom.CoInitialize()` and `pythoncom.CoUninitialize()` around WIA operations.
3. **Simulation Mode**: Automatic fallback to Virtual PDF Spooler & Scanner Simulator on non-Windows hosts or when `SIMULATION_MODE=true`.
4. **AirPrint IPP 2.0**: Maintain RFC 8010/8011 binary compliance on port 631 (or 6310) with mDNS (`_ipp._tcp.local.`).

## Quick Run
- **Windows**: Run `start.bat`
- **Linux/Termux**: `python -m server.main` (Port 5000) & `cd web && node server.js` (Port 3000)
