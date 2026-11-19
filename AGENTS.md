# AI & Autonomous Agent Instructions (`AGENTS.md`)

This repository is an All-in-One Print & Scan Server tailored for an **Epson EcoTank L3110** (or similar L-series USB multifunction printer) hosted on **Windows 11**.

---

## 🏛️ Project Architecture & Invariants

```
[ Clients (Phone/PC) ]
       │
       ├── (Port 631) ───> Python AirPrint IPP / mDNS Listener
       │
       └── (Port 3000) ──> Node.js Express Gateway (Web UI)
                                  │ (Internal Proxy)
                                  ▼
                           Python FastAPI Engine (Port 5000)
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
          Win32 Print Spooler             WIA 2.0 COM Scanner
          (win32print / Shell)            (win32com.client)
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                      Epson EcoTank L3110 (USB)
```

### Critical Development Rules (Must Never Break)
1. **NO C# or .NET Dependencies**:
   - The user explicitly requested **zero C# / .NET**.
   - Do NOT introduce PowerShell cmdlets requiring .NET assemblies, C# wrappers, or `.csproj` files.
   - Hardware integration must remain in **native C/Win32 APIs** via Python `pywin32` (`win32print`, `win32api`) and WIA 2.0 COM automation (`wiaaut.dll` via `win32com.client`).
2. **Thread-Safe COM Management**:
   - Any access to Windows Image Acquisition (`WIA.DeviceManager` or `WIA.CommonDialog`) in Python **MUST** be wrapped in:
     ```python
     import pythoncom
     pythoncom.CoInitialize()
     try:
         # WIA operations
     finally:
         pythoncom.CoUninitialize()
     ```
   - Failing to initialize COM in worker threads causes immediate `0x800401f0 (CoInitialize has not been called)` errors.
3. **Do Not Interfere with Official Epson Drivers**:
   - The Epson L3110 uses the proprietary ESC/P-R raster language.
   - Do NOT try to write raw ESC/P-R raster code directly to USB.
   - Always route print files through the **Windows Print Spooler** (`win32api.ShellExecute("printto", ...)` or `win32print`), allowing the official Epson driver to perform rasterization and ink control.
4. **Separation of Concerns**:
   - `web/`: Presentation layer, static assets, responsive UI, Node.js proxy.
   - `server/`: Python backend, hardware interfaces, AirPrint/mDNS broadcaster.

---

## 📁 Codebase Layout

- `server/main.py`: FastAPI server exposing `/api/print`, `/api/scan`, `/api/printers`, `/api/status`.
- `server/scanner.py`: Windows WIA 2.0 controller (acquires scan buffers, converts via Pillow to PDF/JPEG).
- `server/printer.py`: Windows Spooler integration for submitting jobs to target printers.
- `server/airprint.py`: IPP 2.0 responder (port 631) & Bonjour mDNS announcer for native iOS/macOS printing.
- `server/config.py`: Port, path, and printer name keyword configuration.
- `web/server.js`: Node.js Express proxy and static file server.
- `web/public/`: Vanilla JS, CSS, and HTML5 responsive web dashboard.
- `start.bat` / `start.ps1`: One-click bootstrapper for Windows 11.

---

## 🛠️ Common Operations for Agents

### Installing Dependencies
```bash
# Python
pip install -r requirements.txt

# Node.js
cd web && npm install
```

### Running Locally
```powershell
# Start Python hardware daemon
python -m server.main

# Start Node.js web dashboard
cd web
node server.js
```
