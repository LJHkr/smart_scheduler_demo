from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import deepseek_app as scheduling
from deepseek_client import DeepSeekError, MODEL, is_configured
from explanation_client import explain_schedule
from scheduler import load_employees


HOST = scheduling.HOST
PORT = scheduling.PORT
PROJECT_DIR = scheduling.PROJECT_DIR


def fallback_explanation(question: str, result: dict) -> dict:
    return {
        "answer": "当前排班已经通过 R-01～R-09 的确定性校验。安排时先保证店长值守、饮品制作、收银和最低人数，再在不违反请假、工时及跨日规则的前提下兼顾偏好和工作量。",
        "key_reasons": [
            {
                "title": "硬规则优先",
                "detail": "所有班次只有在技能覆盖、人数、可工作日期和工时约束全部通过后才会展示。",
                "evidence": ["页面规则校验结果为 9 / 9", f"当前共有 {result.get('statistics', {}).get('total_shifts', 0)} 个班次"],
            },
            {
                "title": "偏好属于软目标",
                "detail": "早晚班偏好会被尽量满足，但不会覆盖请假、技能或工时等硬约束。",
                "evidence": ["员工偏好仅参与候选人排序"],
            },
        ],
        "tradeoffs": ["当偏好与硬规则冲突时，以合规为先。"],
        "limitations": [f"DeepSeek 暂时不可用，因此未能针对问题“{question}”生成更细的个性化解释。"],
        "read_only_confirmation": True,
        "source": "deterministic_fallback",
    }


def add_automatic_explanation(result: dict, question: str) -> dict:
    if not result.get("success"):
        return result
    try:
        result["explanation"] = explain_schedule(
            question=question,
            schedule=result["schedule"],
            employees=load_employees(),
            request=result.get("request"),
            changes=result.get("changes"),
        )
        result["explanation"]["source"] = "deepseek"
    except DeepSeekError as error:
        result["explanation"] = fallback_explanation(question, result)
        result["explanation"]["warning"] = str(error)
    return result


def run_new_schedule(user_text: str) -> dict:
    result = scheduling.run_new_schedule(user_text)
    return add_automatic_explanation(
        result,
        "请解释这张排班为什么这样安排，重点说明硬规则覆盖、关键岗位、员工偏好和工作量取舍。",
    )


def run_revision(user_text: str, current_schedule: list[dict], current_request: dict) -> dict:
    result = scheduling.run_revision(user_text, current_schedule, current_request)
    return add_automatic_explanation(
        result,
        "请解释本次为什么这样修改，并说明如何在满足追加需求的同时保持整张排班合规。",
    )


def run_explanation(question: str, current_schedule: list[dict], current_request: dict) -> dict:
    if not current_schedule:
        return {
            "success": False,
            "mode": "explain",
            "needs_base_schedule": True,
            "error": "解释前需要先生成一张排班表。",
        }
    try:
        explanation = explain_schedule(
            question=question,
            schedule=current_schedule,
            employees=load_employees(),
            request=current_request,
        )
        explanation["source"] = "deepseek"
    except DeepSeekError as error:
        base_result = {
            "statistics": {
                "total_shifts": len(current_schedule),
            }
        }
        explanation = fallback_explanation(question, base_result)
        explanation["warning"] = str(error)
    return {
        "success": True,
        "mode": "explain",
        "schedule_unchanged": True,
        "explanation": explanation,
        "agent": {
            "source": "llm" if explanation.get("source") == "deepseek" else "local_fallback",
            "provider": "DeepSeek",
            "model": MODEL if explanation.get("source") == "deepseek" else None,
            "understanding": f"只读解释当前排班：{question}",
            "warning": explanation.get("warning"),
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DeepSeekSchedulerAgent/3.0"

    def send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.send_bytes((PROJECT_DIR / "static" / "agent_v3.html").read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/api/config":
            self.send_json({"enabled": is_configured(), "provider": "DeepSeek", "model": MODEL, "features": ["new", "append", "explain"]})
            return
        if self.path == "/api/health":
            self.send_json({"status": "ok", "deepseek_configured": is_configured(), "version": 3})
            return
        self.send_json({"error": "页面不存在"}, HTTPStatus.NOT_FOUND)

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
                raise ValueError("请输入自然语言需求或问题")
            mode = body.get("mode", "new")
            schedule = body.get("current_schedule") or []
            request = body.get("current_request") or {}
            if mode == "new":
                result = run_new_schedule(text)
            elif mode == "append":
                result = run_revision(text, schedule, request)
            elif mode == "explain":
                result = run_explanation(text, schedule, request)
            else:
                raise ValueError("不支持的 Agent 模式")
            self.send_json(result)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.send_json({"error": "Agent 处理失败", "detail": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DeepSeek 可解释排班 Agent：http://{HOST}:{PORT}")
    print("功能：从0排表 / 追加需求 / 只读解释")
    print("状态：" + ("API Key 已配置" if is_configured() else "未配置 Key，将使用有限降级能力"))
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
