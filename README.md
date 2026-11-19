# Epson L3110 All-in-One Print & Scan Server (Windows 11)

A hybrid network print & scan server designed for an **Epson EcoTank L3110** (or similar L-series multifunction) connected via USB to a **Windows 11 PC**.

This turns your USB-only printer into a **network wireless printer** with **Apple AirPrint** and a **Web Dashboard** for browser-based printing and scanning from any phone, tablet, or laptop on your local Wi-Fi.

---

## 🌟 Key Features

1. **📱 Apple AirPrint Support**:
   - Broadcasts native Bonjour / mDNS (`_ipp._tcp.local.`) on port `631`.
   - iPhones, iPads, and Macs discover the USB Epson printer automatically in the native iOS **"Share → Print"** menu. No apps needed.
2. **🖨️ Wireless Web Printing**:
   - Drag-and-drop PDFs, images, or documents from any device's browser.
   - Forwards jobs directly into the native Windows Print Spooler (`winspool.drv`), letting official Epson drivers handle color management and rasterization.
3. **📄 Remote Flatbed Scanning**:
   - Accesses the scanner via **Windows Image Acquisition (WIA 2.0 COM)**.
   - Choose resolution (150, 300, 600 DPI) and color mode (Full Color, Grayscale, B&W).
   - Generates searchable single-page/multi-page **PDFs** or high-resolution **JPEG/PNG** files.
   - Immediate preview in browser with one-click direct download to your phone or PC.
4. **⚙️ Zero .NET / Zero C# Dependency**:
   - Built cleanly with **Node.js** (Web UI & Gateway) and **Python** (WIA COM & Win32 Spooler automation).

---

## 🏗️ Architecture

```
[ iPhone / Android / Laptop ]
            │
            ├── (Port 631) ───> Python AirPrint IPP Responder ──┐
            │                                                   │
            └── (Port 3000) ──> Node.js Web Dashboard            │
                                       │ (Internal Proxy)       │
                                       ▼                        │
                                Python FastAPI Engine (Port 5000)
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             Win32 Print Spooler                 WIA 2.0 COM Scanner
                     │                                   │
                     └─────────────┬─────────────────────┘
                                   ▼
                       Epson EcoTank L3110 (USB)
```

---

## 🚀 Quick Start on Windows 11

### 1. Prerequisites
- **Epson L3110 Drivers Installed**: Ensure you can print and scan locally from Windows.
- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/) (Make sure to check *"Add Python to PATH"* during install).
- **Node.js LTS**: Download from [nodejs.org](https://nodejs.org/).

### 2. Run with One Click
Double-click `start.bat` (or run `./start.ps1` in PowerShell).

The startup script will automatically:
1. Verify Python & Node.js.
2. Install Python dependencies (`pip install -r requirements.txt`).
3. Install Web dependencies (`npm install`).
4. Start the Python hardware engine & AirPrint broadcaster.
5. Launch the Node.js web dashboard and open `http://localhost:3000` in your browser.

---

## 📱 How to Use

### From iPhone, iPad, or Mac (AirPrint)
1. Ensure your Apple device is connected to the same Wi-Fi as your Windows 11 PC.
2. Open any document, photo, or website.
3. Tap **Share** → **Print**.
4. Select **"EPSON L3110 Series"** from the printer list and tap **Print**.

### From Any Device Browser (Web Dashboard)
1. Find your Windows 11 PC's IP address (displayed at the top of the dashboard, e.g., `192.168.1.150`).
2. Open `http://<your-windows-ip>:3000` on your phone or laptop.
3. **To Print**: Drag and drop your file, select number of copies, and click **"Send to Printer"**.
4. **To Scan**: Click the **Scan Station** tab, choose DPI and Format (PDF/JPG), and click **"Start Scan Now"**. Download the resulting file directly to your phone.

---

## 🔒 Windows Firewall Note

If other devices on your Wi-Fi cannot open the Web Dashboard or discover the AirPrint printer, allow ports through the Windows Firewall:
- **Port 3000 (TCP)**: Web Dashboard.
- **Port 631 (TCP)**: AirPrint IPP.
- **Port 5353 (UDP)**: mDNS / Bonjour discovery (normally allowed by default).

To allow them quickly in PowerShell (Run as Administrator):
```powershell
New-NetFirewallRule -DisplayName "Epson Web Dashboard" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Epson AirPrint IPP" -Direction Inbound -LocalPort 631 -Protocol TCP -Action Allow
```
