/**
 * Node.js Web Dashboard & API Proxy Server
 * Serves the responsive web frontend and bridges requests to the Python FastAPI hardware backend.
 */

const express = require('express');
const path = require('path');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://127.0.0.1:5000';

// Serve frontend static files
app.use(express.static(path.join(__dirname, 'public')));

// Proxy all /api requests to the Python Hardware Engine
app.use(
  '/api',
  createProxyMiddleware({
    target: PYTHON_BACKEND_URL,
    changeOrigin: true,
    onError: (err, req, res) => {
      console.error('[Proxy Error] Could not connect to Python backend:', err.message);
      res.status(503).json({
        error: 'Hardware engine offline',
        message: 'Ensure the Python backend (server/main.py) is running on port 5000.'
      });
    }
  })
);

// Fallback to index.html for SPA navigation
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`=======================================================`);
  console.log(`  Epson Print & Scan Web Dashboard Active!`);
  console.log(`  Local Access:      http://localhost:${PORT}`);
  console.log(`  Network Access:    http://0.0.0.0:${PORT} (on your Wi-Fi)`);
  console.log(`  Hardware Backend:  ${PYTHON_BACKEND_URL}`);
  console.log(`=======================================================`);
});
