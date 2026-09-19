from __future__ import annotations

import json
from http import HTTPStatus
from http.server import ThreadingHTTPServer

import deepseek_app_v5 as base
from request_guard import detect_underdetermined_request


HOST = base.HOST
PORT = base.PORT


def unable_result(mode: str, detected: dict) -> dict:
    return {
        "success": False,
        "mode": mode,
        "unable_to_determine": True,
        "needs_clarification": True,
        "preserve_current": mode == "append",
        "reason": detected["reason"],
        "missing_data": detected["missing_data"],
        "clarification_question": detected["clarification_question"],
    }


class Handler(base.Handler):
    server_version = "DeepSeekSchedulerAgent/6.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self.send_json({"status": "ok", "version": 6, "supports_unable_to_determine": True})
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/agent":
            self.send_json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 500_000:
                raise ValueError("请求内容为空或过大")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(body.get("request", "")).strip()
            if not text:
                raise ValueError("请输入需求或问题")
            mode = body.get("mode", "new")
            schedule = body.get("current_schedule") or []
            request = body.get("current_request") or {}
            if mode in ("new", "append"):
                detected = detect_underdetermined_request(text)
                if detected:
                    self.send_json(unable_result(mode, detected))
                    return
            if mode == "new":
                result = base.run_new_schedule(text)
            elif mode == "append":
                result = base.run_revision(text, schedule, request)
            elif mode == "explain":
                result = base.run_explanation(text, schedule)
            else:
                raise ValueError("不支持的模式")
            self.send_json(result)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.send_json({"error": "处理失败", "detail": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"智能排班助手：http://{HOST}:{PORT}")
    print("功能：排班 / 追加 / 用户解释 / 无法判断边界 / 文件导出")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
