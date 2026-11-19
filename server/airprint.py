"""AirPrint (IPP 2.0 & mDNS / Bonjour) Responder for Epson L3110 on Windows."""

import socket
import logging
import threading
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from zeroconf import Zeroconf, ServiceInfo

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
        # Silence verbose request logs
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

        # Locate document data start (after end-of-attributes-tag 0x03)
        doc_offset = -1
        for i in range(8, len(post_data)):
            if post_data[i] == 0x03:
                doc_offset = i + 1
                break

        # Process Operations
        if operation_id in (IPP_OP_PRINT_JOB, IPP_OP_VALIDATE_JOB):
            if operation_id == IPP_OP_PRINT_JOB and doc_offset > 0 and doc_offset < len(post_data):
                doc_bytes = post_data[doc_offset:]
                # Save incoming PDF or raster
                job_file = SPOOL_DIR / f"airprint_job_{request_id}.pdf"
                job_file.write_bytes(doc_bytes)
                logger.info(f"Received AirPrint document ({len(doc_bytes)} bytes). Spooling to printer...")
                try:
                    print_file(str(job_file))
                except Exception as e:
                    logger.error(f"Failed to print AirPrint job: {e}")

            # Send Successful-OK Response
            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.end_headers()

            # Construct IPP response header
            response_header = bytearray([
                version_major, version_minor,
                (IPP_STATUS_OK >> 8) & 0xFF, IPP_STATUS_OK & 0xFF,
                (request_id >> 24) & 0xFF, (request_id >> 16) & 0xFF,
                (request_id >> 8) & 0xFF, request_id & 0xFF,
                0x01,  # operation-attributes-tag
                0x47, 0x00, 0x12, ord('a'), ord('t'), ord('t'), ord('r'), ord('i'), ord('b'), ord('u'), ord('t'), ord('e'), ord('s'), ord('-'), ord('c'), ord('h'), ord('a'), ord('r'), ord('s'), ord('e'), ord('t'),
                0x00, 0x05, ord('u'), ord('t'), ord('f'), ord('-'), ord('8'),
                0x48, 0x00, 0x1b, ord('a'), ord('t'), ord('t'), ord('r'), ord('i'), ord('b'), ord('u'), ord('t'), ord('e'), ord('s'), ord('-'), ord('n'), ord('a'), ord('t'), ord('u'), ord('r'), ord('a'), ord('l'), ord('-'), ord('l'), ord('a'), ord('n'), ord('g'), ord('u'), ord('a'), ord('g'), ord('e'),
                0x00, 0x02, ord('e'), ord('n'),
                0x03   # end-of-attributes-tag
            ])
            self.wfile.write(response_header)

        elif operation_id == IPP_OP_GET_PRINTER_ATTRIBUTES:
            self.send_response(200)
            self.send_header("Content-Type", "application/ipp")
            self.end_headers()

            response = bytearray([
                version_major, version_minor,
                (IPP_STATUS_OK >> 8) & 0xFF, IPP_STATUS_OK & 0xFF,
                (request_id >> 24) & 0xFF, (request_id >> 16) & 0xFF,
                (request_id >> 8) & 0xFF, request_id & 0xFF,
                0x01,  # operation-attributes-tag
                0x47, 0x00, 0x12, ord('a'), ord('t'), ord('t'), ord('r'), ord('i'), ord('b'), ord('u'), ord('t'), ord('e'), ord('s'), ord('-'), ord('c'), ord('h'), ord('a'), ord('r'), ord('s'), ord('e'), ord('t'),
                0x00, 0x05, ord('u'), ord('t'), ord('f'), ord('-'), ord('8'),
                0x03   # end-of-attributes-tag
            ])
            self.wfile.write(response)
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
        self.zeroconf: Optional[Zeroconf] = None
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
            logger.warning(f"Could not bind IPP port {self.port}: {e}. (Port may require administrator privileges).")

        # 2. Start mDNS Broadcaster
        try:
            self.zeroconf = Zeroconf()
            printer_name = get_target_printer()

            # Prepare Apple AirPrint TXT Properties
            desc = {
                b"txtvers": b"1",
                b"qtotal": b"1",
                b"rp": b"printers/epson",
                b"ty": printer_name.encode("utf-8"),
                b"adminurl": f"http://{LOCAL_IP}:{self.port}".encode("utf-8"),
                b"pdl": b"application/pdf,image/urf,image/jpeg",
                b"Color": b"T",
                b"Duplex": b"F",
                b"URF": b"W8,SRGB24,CP1,RS300"
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

        except Exception as e:
            logger.error(f"Failed to start AirPrint mDNS service: {e}")

    def stop(self):
        if self.zeroconf:
            self.zeroconf.close()
        if self.httpd:
            self.httpd.shutdown()
