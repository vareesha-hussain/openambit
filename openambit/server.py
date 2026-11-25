import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import autostart, effects

WEB = Path(__file__).parent / "web"


def make_handler(engine, quit_cb):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/api/state":
                return self._json({
                    "state": engine.state, "effects": list(effects.EFFECTS),
                    "preview": [[int(c) for c in px] for px in engine.preview],
                    "audio_error": engine.audio.error,
                    "connected": engine.dev.connected,
                    "autostart": autostart.is_enabled(),
                })
            f = WEB / ("index.html" if self.path in ("/", "") else self.path.lstrip("/"))
            if f.is_file() and WEB in f.resolve().parents:
                b = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html" if f.suffix == ".html" else "text/plain")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            else:
                self.send_error(404)

        def do_POST(self):
            # Reject cross-site requests: only same-origin localhost pages may control the lights.
            origin = self.headers.get("Origin")
            if origin and origin.split("//")[-1] != self.headers.get("Host"):
                return self._json({"error": "bad origin"}, 403)
            if self.path == "/api/update":
                n = int(self.headers.get("Content-Length", 0))
                engine.update(json.loads(self.rfile.read(n) or b"{}"))
                return self._json({"ok": True})
            if self.path == "/api/autostart":
                n = int(self.headers.get("Content-Length", 0))
                ok, msg = autostart.set_enabled(bool(json.loads(self.rfile.read(n) or b"{}").get("enabled")))
                return self._json({"ok": ok, "message": msg})
            if self.path == "/api/quit":
                self._json({"ok": True})
                quit_cb()
                return
            self.send_error(404)

    return H


def serve(engine, host="127.0.0.1", port=8765):
    holder = {}
    srv = ThreadingHTTPServer((host, port), make_handler(
        engine, lambda: threading.Thread(target=holder["srv"].shutdown, daemon=True).start()))
    holder["srv"] = srv
    srv.serve_forever()
