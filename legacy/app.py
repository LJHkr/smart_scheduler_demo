from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scheduler import generate_schedule


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000


class SchedulerHandler(BaseHTTPRequestHandler):
    server_version = "SmartSchedulerDemo/1.0"

    def _send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(content, "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            content = (BASE_DIR / "static" / "index.html").read_bytes()
            self._send_bytes(content, "text/html; charset=utf-8")
            return
        if self.path == "/api/health":
            self._send_json({"status": "ok", "service": "智能排班助手"})
            return
        self._send_json({"error": "页面不存在"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/schedule":
            self._send_json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                raise ValueError("请求内容为空或过大")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            request_text = str(body.get("request", "")).strip()
            if not request_text:
                raise ValueError("请输入排班需求")
            self._send_json(generate_schedule(request_text))
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:  # Demo 中保留可读错误，方便现场定位
            self._send_json(
                {"error": "服务处理失败", "detail": str(error)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), SchedulerHandler)
    print(f"智能排班助手已启动：http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
