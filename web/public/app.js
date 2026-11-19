/**
 * Frontend logic for Epson Print & Scan Gateway.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Tab Elements
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  // Status Elements
  const systemStatusBadge = document.getElementById('systemStatusBadge');
  const statusText = document.getElementById('statusText');
  const hostIpDisplay = document.getElementById('hostIpDisplay');
  const airprintStatusDisplay = document.getElementById('airprintStatusDisplay');
  const printerStatusDetail = document.getElementById('printerStatusDetail');
  const scannerStatusDetail = document.getElementById('scannerStatusDetail');

  // Print Elements
  const printForm = document.getElementById('printForm');
  const fileInput = document.getElementById('printFileInput');
  const dropZone = document.getElementById('dropZone');
  const selectedFileName = document.getElementById('selectedFileName');
  const printerSelect = document.getElementById('printerSelect');
  const copiesCount = document.getElementById('copiesCount');
  const printSubmitBtn = document.getElementById('printSubmitBtn');
  const printNotification = document.getElementById('printNotification');

  // Scan Elements
  const triggerScanBtn = document.getElementById('triggerScanBtn');
  const scanDpi = document.getElementById('scanDpi');
  const scanColor = document.getElementById('scanColor');
  const scanFormat = document.getElementById('scanFormat');
  const scanLoader = document.getElementById('scanLoader');
  const scanResult = document.getElementById('scanResult');
  const previewBox = document.getElementById('previewBox');
  const downloadScanBtn = document.getElementById('downloadScanBtn');

  // 1. Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = document.getElementById(btn.dataset.tab);
      if (targetTab) targetTab.classList.add('active');
    });
  });

  // 2. Fetch System Status & Hardware
  async function refreshStatus() {
    try {
      const res = await fetch('/api/status');
      if (!res.ok) throw new Error('Backend unreachable');
      const data = await res.parse ? await res.parse() : await res.json();

      statusText.textContent = 'Online';
      systemStatusBadge.style.display = 'flex';
      hostIpDisplay.textContent = data.host_ip;
      airprintStatusDisplay.textContent = data.airprint_active ? 'Active (Port 631)' : 'Disabled';

      printerStatusDetail.textContent = `Default: ${data.default_printer || 'Epson L3110'}`;
      scannerStatusDetail.textContent = data.scanners_count > 0 
        ? `${data.scanners_count} Scanner(s) Connected` 
        : 'Ready on USB';

    } catch (err) {
      statusText.textContent = 'Offline';
      systemStatusBadge.style.background = 'rgba(239, 68, 68, 0.15)';
      systemStatusBadge.style.color = '#f87171';
    }
  }

  // 3. Load Available Printers
  async function loadPrinters() {
    try {
      const res = await fetch('/api/printers');
      const data = await res.json();
      printerSelect.innerHTML = '<option value="">Auto-Detect (Epson L3110)</option>';
      data.printers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.name;
        opt.textContent = `${p.name} (${p.status})`;
        if (p.is_default || p.is_epson) opt.selected = true;
        printerSelect.appendChild(opt);
      });
    } catch (err) {
      console.warn('Could not load printers list', err);
    }
  }

  // 4. File Drag & Drop
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      selectedFileName.textContent = `Selected: ${fileInput.files[0].name} (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      selectedFileName.textContent = `Selected: ${fileInput.files[0].name} (${(fileInput.files[0].size / 1024 / 1024).toFixed(2)} MB)`;
    }
  });

  // 5. Submit Print Job
  printForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) {
      alert('Please select a file to print.');
      return;
    }

    printSubmitBtn.disabled = true;
    printSubmitBtn.textContent = 'Sending to Print Spooler...';
    printNotification.className = 'notification';
    printNotification.style.display = 'none';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('copies', copiesCount.value);
    if (printerSelect.value) {
      formData.append('printer', printerSelect.value);
    }

    try {
      const res = await fetch('/api/print', {
        method: 'POST',
        body: formData
      });

      const result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Printing failed');

      printNotification.className = 'notification success';
      printNotification.textContent = `✅ Successfully submitted to ${result.result.printer} (${result.result.copies} copy/copies)!`;
      printForm.reset();
      selectedFileName.textContent = '';
    } catch (err) {
      printNotification.className = 'notification error';
      printNotification.textContent = `❌ Error: ${err.message}`;
    } finally {
      printSubmitBtn.disabled = false;
      printSubmitBtn.textContent = 'Send to Printer';
    }
  });

  // 6. Trigger Flatbed Scan
  triggerScanBtn.addEventListener('click', async () => {
    triggerScanBtn.disabled = true;
    scanLoader.classList.add('active');
    scanResult.classList.remove('active');
    previewBox.innerHTML = '';

    const params = new URLSearchParams({
      dpi: scanDpi.value,
      color_mode: scanColor.value,
      format: scanFormat.value
    });

    try {
      const res = await fetch(`/api/scan?${params.toString()}`, {
        method: 'POST'
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Scan failed');

      // Populate Result Preview
      const fileUrl = data.download_url;
      downloadScanBtn.href = fileUrl;
      downloadScanBtn.download = data.filename;

      if (data.format === 'pdf') {
        previewBox.innerHTML = `
          <div style="padding: 2rem; background: rgba(0,0,0,0.3); border-radius: 8px;">
            <p style="font-size: 2.5rem; margin-bottom: 0.5rem;">📄</p>
            <p><strong>${data.filename}</strong></p>
            <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem;">PDF Document (${(data.size_bytes / 1024).toFixed(1)} KB)</p>
          </div>
        `;
      } else {
        previewBox.innerHTML = `<img src="${fileUrl}" alt="Scanned Document Preview" />`;
      }

      scanResult.classList.add('active');
    } catch (err) {
      alert(`Scanning Error: ${err.message}`);
    } finally {
      triggerScanBtn.disabled = false;
      scanLoader.classList.remove('active');
    }
  });

  // Init
  refreshStatus();
  loadPrinters();
  setInterval(refreshStatus, 10000);
});
