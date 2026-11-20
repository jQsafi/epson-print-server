"""AirPrint (IPP 2.0 & mDNS / Bonjour) Responder with graceful dependency fallback."""

import socket
import logging
import threading
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

from .config import LOCAL_IP, IPP_PORT, SPOOL_DIR
from .printer import print_file, get_target_printer

logger = logging.getLogger("airprint")

IPP_STATUS_OK = 0x0000
IPP_OP_PRINT_JOB = 0x0002
IPP_OP_VALIDATE_JOB = 0x0004
IPP_OP_GET_PRINTER_ATTRIBUTES = 0x000B


class IPPRequestHandler(BaseHTTPRequestHandler):
    """Handles IPP 2.0 requests from iOS (AirPrint) and macOS clients."""

    def log_message(self, format, *args):
        return

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if len(post_data) < 8:
            self.send_error(400, "Bad IPP Request")
            return

        version_major = post_data[0]
        version_minor = post_data[1]
        operation_id = (post_data[2] << 8) | post_data[3]
        request_id = (post_data[4] << 24) | (post_data[5] << 16) | (post_data[6] << 8) | post_data[7]

        logger.info(f"IPP Request: Op 0x{operation_id:04x}, ReqID {request_id} from {self.client_address[0]}")

        doc_offset = -1
        for i in range(8, len(post_data)):
            if post_data[i] == 0x03:
                doc_offset = i + 1
                break

        if operation_id in (IPP_OP_PRINT_JOB, IPP_OP_VALIDATE_JOB):
            if operation_id == IPP_OP_PRINT_JOB and doc_offset > 0 and doc_offset < len(post_data):
                doc_bytes = post_data[doc_offset:]
                if doc_bytes.startswith(b"%PDF"):
                    ext = "pdf"
                elif doc_bytes.startswith(b"\xff\xd8\xff"):
                    ext = "jpg"
                elif doc_bytes.startswith(b"\x89PNG"):
                    ext = "png"
                else:
                    ext = "pdf"

                job_file = SPOOL_DIR / f"airprint_job_{request_id}.{ext}"
                job_file.write_bytes(doc_bytes)
                logger.info(f"Received AirPrint document ({len(doc_bytes)} bytes, ext: .{ext}). Spooling...")
                try:
                    print_file(str(job_file))
                except Exception as e:
                    logger.error(f"Failed to print AirPrint job: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.end_headers()

            response_header = bytearray([
                version_major, version_minor,
                (IPP_STATUS_OK >> 8) & 0xFF, IPP_STATUS_OK & 0xFF,
                (request_id >> 24) & 0xFF, (request_id >> 16) & 0xFF,
                (request_id >> 8) & 0xFF, request_id & 0xFF,
                0x01,
                0x47, 0x00, 0x12, ord('a'), ord('t'), ord('t'), ord('r'), ord('i'), ord('b'), ord('u'), ord('t'), ord('e'), ord('s'), ord('-'), ord('c'), ord('h'), ord('a'), ord('r'), ord('s'), ord('e'), ord('t'),
                0x00, 0x05, ord('u'), ord('t'), ord('f'), ord('-'), ord('8'),
                0x48, 0x00, 0x1b, ord('a'), ord('t'), ord('t'), ord('r'), ord('i'), ord('b'), ord('u'), ord('t'), ord('e'), ord('s'), ord('-'), ord('n'), ord('a'), ord('t'), ord('u'), ord('r'), ord('a'), ord('l'), ord('-'), ord('l'), ord('a'), ord('n'), ord('g'), ord('u'), ord('a'), ord('g'), ord('e'),
                0x00, 0x02, ord('e'), ord('n'),
                0x03
            ])
            self.wfile.write(response_header)

        elif operation_id == IPP_OP_GET_PRINTER_ATTRIBUTES:
            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.end_headers()

            printer_name = get_target_printer()

            def make_attr(tag, name, val):
                nb = name.encode('utf-8')
                return bytes([tag]) + len(nb).to_bytes(2, 'big') + nb + len(val).to_bytes(2, 'big') + val

            def make_val(tag, val):
                return bytes([tag, 0x00, 0x00]) + len(val).to_bytes(2, 'big') + val

            res = bytearray([
                version_major, version_minor,
                (IPP_STATUS_OK >> 8) & 0xFF, IPP_STATUS_OK & 0xFF,
                (request_id >> 24) & 0xFF, (request_id >> 16) & 0xFF,
                (request_id >> 8) & 0xFF, request_id & 0xFF,
            ])
            # Group 1: Operation Attributes
            res += bytes([0x01])
            res += make_attr(0x47, 'attributes-charset', b'utf-8')
            res += make_attr(0x48, 'attributes-natural-language', b'en')

            # Group 4: Printer Attributes (Required by Android / Mopria / CUPS)
            res += bytes([0x04])
            res += make_attr(0x42, 'printer-name', printer_name.encode('utf-8'))
            res += make_attr(0x23, 'printer-state', (3).to_bytes(4, 'big'))
            res += make_attr(0x44, 'printer-state-reasons', b'none')
            res += make_attr(0x22, 'printer-is-accepting-jobs', b'\x01')
            res += make_attr(0x45, 'printer-uri-supported', f'ipp://{LOCAL_IP}:{self.server.server_port}/printers/epson'.encode('utf-8'))
            res += make_attr(0x44, 'uri-authentication-supported', b'none')
            res += make_attr(0x44, 'uri-security-supported', b'none')
            res += make_attr(0x23, 'operations-supported', (2).to_bytes(4, 'big'))
            res += make_val(0x23, (4).to_bytes(4, 'big'))
            res += make_val(0x23, (11).to_bytes(4, 'big'))
            res += make_attr(0x49, 'document-format-supported', b'application/pdf')
            res += make_val(0x49, b'image/pwg-raster')
            res += make_val(0x49, b'image/urf')
            res += make_val(0x49, b'image/jpeg')
            res += make_val(0x49, b'application/octet-stream')
            res += bytes([0x03])

            self.wfile.write(res)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.end_headers()
            self.wfile.write(bytearray([
                version_major, version_minor,
                (IPP_STATUS_OK >> 8) & 0xFF, IPP_STATUS_OK & 0xFF,
                (request_id >> 24) & 0xFF, (request_id >> 16) & 0xFF,
                (request_id >> 8) & 0xFF, request_id & 0xFF,
                0x03
            ]))


class AirPrintService:
    """Manages mDNS (Bonjour) announcement and background IPP listener."""

    def __init__(self, port: int = IPP_PORT):
        self.port = port
        self.zeroconf = None
        self.httpd: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self):
        # 1. Start IPP HTTP Listener
        try:
            self.httpd = HTTPServer(("0.0.0.0", self.port), IPPRequestHandler)
            self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.server_thread.start()
            logger.info(f"AirPrint IPP listener active on port {self.port}")
        except Exception as e:
            logger.warning(f"Could not bind IPP port {self.port}: {e}")

        # 2. Start mDNS Broadcaster (if zeroconf installed)
        try:
            from zeroconf import Zeroconf, ServiceInfo
            self.zeroconf = Zeroconf()
            printer_name = get_target_printer()

            desc = {
                b"txtvers": b"1",
                b"qtotal": b"1",
                b"rp": b"printers/epson",
                b"ty": printer_name.encode("utf-8"),
                b"adminurl": f"http://{LOCAL_IP}:{self.port}".encode("utf-8"),
                b"pdl": b"application/pdf,image/pwg-raster,image/urf,image/jpeg,application/octet-stream",
                b"Color": b"T",
                b"Duplex": b"F",
                b"URF": b"W8,SRGB24,CP1,RS300",
                b"UUID": b"43872242-70b5-4b77-8898-0c679a9415c4",
                b"product": f"({printer_name})".encode("utf-8"),
                b"usb_MFG": b"EPSON",
                b"usb_MDL": b"L3310 Series",
                b"mopria-certified": b"1.3"
            }

            info = ServiceInfo(
                "_ipp._tcp.local.",
                f"{printer_name}._ipp._tcp.local.",
                addresses=[socket.inet_aton(LOCAL_IP)],
                port=self.port,
                properties=desc,
                server=f"{socket.gethostname()}.local."
            )

            self.zeroconf.register_service(info)
            logger.info(f"AirPrint mDNS registered: '{printer_name}' at {LOCAL_IP}:{self.port}")
        except ImportError:
            logger.info("Zeroconf module not installed. IPP listener active; mDNS broadcast skipped.")
        except Exception as e:
            logger.error(f"Failed to start AirPrint mDNS service: {e}")

    def stop(self):
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception:
                pass
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
