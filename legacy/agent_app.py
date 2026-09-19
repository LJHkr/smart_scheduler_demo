from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from llm_client import LLMClientError, interpret_with_llm, public_llm_status
from scheduler import DAYS, SHIFTS, generate_schedule


BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000


def _to_local_request(parsed: dict) -> str:
    days = parsed.get("days") or DAYS
    shifts = parsed.get("shifts") or SHIFTS
    if days == DAYS:
        parts = ["生成完整一周排班"]
    elif days == DAYS[:5]:
        parts = ["生成工作日排班"]
    elif days == ["周六", "周日"]:
        parts = ["生成周末排班"]
    else:
        parts = ["生成" + "、".join(days) + "排班"]
    if shifts == ["早班"]:
        parts.append("只排早班")
    elif shifts == ["晚班"]:
        parts.append("只排晚班")
    if not parsed.get("respect_preferences", True):
        parts.append("不考虑偏好")
    if not parsed.get("balance_workload", True):
        parts.append("不需要均衡")
    return "，".join(parts)


def run_agent(user_text: str) -> dict:
    try:
        interpretation = interpret_with_llm(user_text)
        if interpretation.get("needs_clarification"):
            return {
                "success": False,
                "needs_clarification": True,
                "clarification_question": interpretation["clarification_question"],
                "agent": {
                    "source": "llm",
                    "model": interpretation.get("model"),
                    "understanding": interpretation.get("understanding"),
                },
            }
        result = generate_schedule(_to_local_request(interpretation))
        result["request"]["original_text"] = user_text
        result["request"]["llm_interpretation"] = interpretation
        result["agent"] = {
            "source": "llm",
            "model": interpretation.get("model"),
            "understanding": interpretation.get("understanding"),
            "fallback": False,
        }
        return result
    except LLMClientError as error:
        result = generate_schedule(user_text)
        result["agent"] = {
            "source": "local_fallback",
            "model": None,
            "understanding": "LLM 不可用，已使用本地关键词解析继续生成排班。",
            "fallback": True,
            "warning": str(error),
        }
        return result


class AgentHandler(BaseHTTPRequestHandler):
    server_version = "SmartSchedulerAgent/2.0"

    def _send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        self._send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send_bytes(
                (BASE_DIR / "static" / "agent.html").read_bytes(),
                "text/html; charset=utf-8",
            )
            return
        if self.path == "/api/config":
            self._send_json(public_llm_status())
            return
        if self.path == "/api/health":
            self._send_json({"status": "ok", "llm": public_llm_status()})
            return
        self._send_json({"error": "页面不存在"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/agent":
            self._send_json({"error": "接口不存在"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100_000:
                raise ValueError("请求内容为空或过大")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            user_text = str(body.get("request", "")).strip()
            if not user_text:
                raise ValueError("请输入自然语言排班需求")
            self._send_json(run_agent(user_text))
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self._send_json(
                {"error": "Agent 处理失败", "detail": str(error)},
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AgentHandler)
    status = public_llm_status()
    mode = f"LLM：{status['model']}" if status["enabled"] else "本地降级模式（尚未配置 API Key）"
    print(f"智能排班 Agent 已启动：http://{HOST}:{PORT}")
    print(f"当前模式：{mode}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
