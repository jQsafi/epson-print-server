# Windows 11 Host Setup & Operational Guide

This guide walks you through setting up your Windows 11 PC as a dedicated, headless or interactive Print & Scan Server for an **Epson EcoTank L3110** (or similar USB multifunction printer).

---

## 📋 Step 1: Install Official Epson Drivers

For Windows to communicate with the USB hardware, install the official Epson software:
1. Connect the Epson L3110 to your Windows 11 PC via USB and power it on.
2. Download the official **Printer Driver** and **Scanner Driver (Epson Scan 2)** from the official Epson support page.
3. Test locally in Windows:
   - Print a test page from **Settings → Bluetooth & devices → Printers & scanners → EPSON L3110 Series**.
   - Open **Windows Fax and Scan** or **Windows Scan** to confirm flatbed scanning works.

---

## 🐍 Step 2: Install Runtimes (Zero C# / Zero .NET Needed)

### 1. Python 3.10+
- Download from [python.org/downloads](https://www.python.org/downloads/).
- **CRITICAL**: Check the box **"Add python.exe to PATH"** on the first installer screen.

### 2. Node.js LTS
- Download the LTS installer from [nodejs.org](https://nodejs.org/).
- Run the installer with default options.

---

## 🛡️ Step 3: Configure Windows Firewall

To allow other devices on your Wi-Fi (such as iPhones and Android devices) to access the server, run the following in **PowerShell (Run as Administrator)**:

```powershell
# 1. Allow Web Dashboard (Port 3000)
New-NetFirewallRule -DisplayName "Epson Web Dashboard" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow

# 2. Allow Apple AirPrint IPP (Port 631)
New-NetFirewallRule -DisplayName "Epson AirPrint IPP" -Direction Inbound -LocalPort 631 -Protocol TCP -Action Allow

# 3. Allow mDNS / Bonjour Discovery (Port 5353)
New-NetFirewallRule -DisplayName "Epson mDNS Discovery" -Direction Inbound -LocalPort 5353 -Protocol UDP -Action Allow
```

---

## 🚀 Step 4: Starting the Server

### Interactive Mode (Terminal / Development)
Double-click `start.bat` in the repository root.
This will:
- Check and install any missing Python and Node dependencies.
- Launch the Python hardware engine.
- Launch the Node.js web dashboard.
- Automatically open `http://localhost:3000`.

---

## 🔄 Step 5: Run Automatically on Windows 11 Boot (Optional)

To keep the print and scan server running 24/7 without having to manually start it:

### Method A: Windows Startup Folder (Easiest)
1. Press `Win + R`, type `shell:startup`, and hit Enter.
2. Create a shortcut to `start.bat` inside this Startup folder.
3. The server will launch every time you log into Windows.

### Method B: As a Silent Windows Background Service (via NSSM)
1. Download **NSSM** (Non-Sucking Service Manager) from [nssm.cc](https://nssm.cc/).
2. Run in PowerShell as Administrator:
   ```powershell
   nssm install EpsonPrintServer "C:\path\to\epson-print-server\start.bat"
   nssm start EpsonPrintServer
   ```
   Now the server runs automatically in the background even before logging in!

---

## ❓ Troubleshooting

| Issue | Cause | Fix |
| :--- | :--- | :--- |
| **AirPrint not appearing on iPhone** | mDNS blocked or IPP port 631 blocked | Run the firewall rule for port `631` (TCP) and `5353` (UDP). Ensure both devices are on the same Wi-Fi SSID. |
| **Scan fails with "No WIA scanner found"** | Scanner offline or driver missing | Ensure Epson Scan 2 driver is installed and the printer's power LED is solid green. |
| **Print job queues but doesn't print** | USB disconnected or paper tray empty | Check Windows Print Queue under Settings → Printers & Scanners. |
