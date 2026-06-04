import socketserver
import json
from decimal import Decimal
from .handlers import handle

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)

class TCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        for raw in self.rfile:
            try:
                print("TCP Received raw:", raw)

                msg = json.loads(raw.decode("utf-8").strip())
                print("Parsed JSON:", msg)

                resp = handle(msg)
                print("Response:", resp)

            except Exception as e:
                resp = {"ok": False, "error": f"Invalid request: {e}"}

            # 🚀 Fix lỗi Decimal bằng default=decimal_default
            self.wfile.write((json.dumps(resp, default=decimal_default) + "\n").encode("utf-8"))

def run_tcp(host, port):
    server = socketserver.ThreadingTCPServer((host, port), TCPHandler)
    print(f"[TCP] Listening {host}:{port}")
    server.serve_forever()
