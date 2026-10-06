"""Calculator back-end entry point.

A dependency-free HTTP server (Python standard library only) that:

* Exposes the REST API required by the assignment:
    POST   /api/calculate        -- evaluate an expression, persist it
    GET    /api/history          -- list stored history (newest first)
    DELETE /api/history/<id>     -- delete one history record
* Serves the front-end static files (so the whole system is reachable
  from a single public URL).

Run:
    python main.py [--port 8000] [--host 0.0.0.0]

The listening port is also taken from the ``PORT`` environment variable
(which most cloud deployment platforms inject automatically).
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Make ``import src...`` work when launched as a script.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.model.database import init_db, add_record, get_all, delete_record  # noqa: E402
from src.service.evaluator import evaluate, EvalError  # noqa: E402

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY = 4096

# CORS is enabled permissively so the API can also be tested cross-origin.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class CalculatorHandler(BaseHTTPRequestHandler):
    server_version = "CalculatorBackend/1.0"

    # ---- low-level helpers -------------------------------------------------
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path):
        # Map "/" to index.html.
        rel = path.lstrip("/")
        if rel == "" or rel == "index.html":
            rel = "index.html"
        file_path = os.path.normpath(os.path.join(STATIC_DIR, rel))
        # Prevent path traversal outside STATIC_DIR.
        if not file_path.startswith(os.path.normpath(STATIC_DIR)):
            self._send_json(403, {"error": "forbidden"})
            return
        if not os.path.isfile(file_path):
            self._send_json(404, {"error": "not found"})
            return
        content_type = self._guess_type(file_path)
        with open(file_path, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _guess_type(file_path):
        if file_path.endswith(".html"):
            return "text/html; charset=utf-8"
        if file_path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if file_path.endswith(".css"):
            return "text/css; charset=utf-8"
        if file_path.endswith(".json"):
            return "application/json; charset=utf-8"
        if file_path.endswith(".svg"):
            return "image/svg+xml"
        return "application/octet-stream"

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return b""
        if length > MAX_BODY:
            return None  # signal too-large
        return self.rfile.read(length)

    # ---- HTTP verbs --------------------------------------------------------
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/history":
            self._handle_get_history()
        elif path == "/api/calculate":
            self._send_json(405, {"error": "请使用 POST 方法调用 /api/calculate"})
        else:
            self._send_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/calculate":
            self._handle_calculate()
        else:
            self._send_json(404, {"error": "not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/history/"):
            try:
                record_id = int(parsed.path.rsplit("/", 1)[-1])
            except ValueError:
                self._send_json(400, {"error": "非法的记录 id"})
                return
            self._handle_delete(record_id)
        else:
            self._send_json(404, {"error": "not found"})

    # ---- API handlers ------------------------------------------------------
    def _handle_calculate(self):
        raw = self._read_body()
        if raw is None:
            self._send_json(413, {"error": "请求体过大"})
            return
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "请求体不是合法 JSON"})
            return

        expression = data.get("expression")
        if not isinstance(expression, str) or not expression.strip():
            self._send_json(400, {"error": "缺少 expression 字段或为空"})
            return

        try:
            result = evaluate(expression)
        except EvalError as exc:
            self._send_json(400, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"服务器内部错误：{exc}"})
            return

        record = add_record(expression.strip(), result)
        self._send_json(200, record)

    def _handle_get_history(self):
        try:
            history = get_all()
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"读取历史失败：{exc}"})
            return
        self._send_json(200, {"history": history})

    def _handle_delete(self, record_id):
        try:
            ok = delete_record(record_id)
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"删除失败：{exc}"})
            return
        if ok:
            self._send_json(200, {"deleted": True, "id": record_id})
        else:
            self._send_json(404, {"error": f"id={record_id} 的记录不存在"})

    # Quieter default logging.
    def log_message(self, fmt, *args):
        sys.stderr.write("[backend] " + (fmt % args) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Calculator back-end server")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", os.environ.get("PORT_ENV", "8000"))),
    )
    args = parser.parse_args()

    init_db()
    server = ThreadingHTTPServer((args.host, args.port), CalculatorHandler)
    print(f"Calculator backend listening on http://{args.host}:{args.port}")
    print(f"Serving front-end from: {STATIC_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
