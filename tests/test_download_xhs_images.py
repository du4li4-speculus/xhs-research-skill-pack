import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 64


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(PNG)

    def log_message(self, fmt, *args):
        pass


def main():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        payload = {
            "success": True,
            "data": {
                "data": {
                    "note": {
                        "imageList": [
                            {"urlDefault": f"http://127.0.0.1:{port}/1", "width": 1080, "height": 1440},
                            {"urlPre": f"http://127.0.0.1:{port}/2", "width": 1080, "height": 1440},
                        ]
                    }
                }
            }
        }
        src = td / "detail.json"
        out = td / "out"
        src.write_text(json.dumps(payload), encoding="utf-8")
        script = Path(__file__).parents[1] / "scripts" / "download_xhs_images.py"
        cp = subprocess.run(
            [sys.executable, str(script), "--input", str(src), "--out-dir", str(out)],
            capture_output=True,
            text=True,
        )
        assert cp.returncode == 0, cp.stderr + cp.stdout
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["downloaded"] == 2
        assert manifest["failed"] == 0
        for item in manifest["images"]:
            assert Path(item["local_path"]).exists()

    server.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
