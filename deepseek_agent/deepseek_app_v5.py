from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import deepseek_app as scheduling
from deepseek_client import DeepSeekError, MODEL, is_configured
from explanation_client_v2 import explain_for_user
from scheduler import load_employees


HOST = scheduling.HOST
PORT = scheduling.PORT
PROJECT_DIR = scheduling.PROJECT_DIR


def fallback_sentences(schedule: list[dict]) -> list[str]:
    employees = {employee["id"]: employee for employee in load_employees()}
    sentences = []
    for item in schedule:
        for employee_id in item.get("employees", []):
            employee = employees.get(employee_id)
            if employee and employee.get("preferred_shift") == item["shift"]:
                sentences.append(f"因为 {employee_id} 偏好{item['shift']}，所以安排在{item['day']}{item['shift']}。")
            if len(sentences) >= 5:
                return sentences
    return sentences or ["本次安排优先考虑了员工可工作的日期和班次偏好。"]


def attach_user_explanation(result: dict, question: str) -> dict:
    if not result.get("success"):
        return result
    try:
        result["explanation"] = explain_for_user(
            question=question,
            schedule=result["schedule"],
            employees=load_employees(),
            changes=result.get("changes"),
        )
        result["explanation"]["source"] = "deepseek"
    except DeepSeekError:
        result["explanation"] = {
            "sentences": fallback_sentences(result["schedule"]),
            "read_only_confirmation": True,
            "source": "fallback",
        }
    return result


def run_new_schedule(text: str) -> dict:
    return attach_user_explanation(
        scheduling.run_new_schedule(text),
        "请用面向门店用户的简短句子解释这张排班为什么这样安排。",
    )


def run_revision(text: str, schedule: list[dict], request: dict) -> dict:
    return attach_user_explanation(
        scheduling.run_revision(text, schedule, request),
        "请用面向门店用户的简短句子解释本次为什么这样调整。",
    )


def run_explanation(question: str, schedule: list[dict]) -> dict:
    if not schedule:
        return {"success": False, "mode": "explain", "needs_base_schedule": True, "error": "请先生成一张排班表。"}
    try:
        explanation = explain_for_user(
            question=question,
            schedule=schedule,
            employees=load_employees(),
        )
        explanation["source"] = "deepseek"
    except DeepSeekError:
        explanation = {
            "sentences": fallback_sentences(schedule),
            "read_only_confirmation": True,
            "source": "fallback",
        }
    return {
        "success": True,
        "mode": "explain",
        "schedule_unchanged": True,
        "explanation": explanation,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DeepSeekSchedulerAgent/5.0"

    def send_bytes(self, content: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_bytes(json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def _page(self) -> bytes:
        html = (PROJECT_DIR / "static" / "agent_v3.html").read_text(encoding="utf-8")
        html = html.replace("</head>", '<link rel="stylesheet" href="/export_tools.css"></head>', 1)
        toolbar = """<div class="export-bar"><div><span class="export-title">导出当前版本</span><span class="export-hint">Markdown 用于飞书文档，CSV 用于表格复核</span></div><div class="export-actions"><button id="export-md" class="export-btn" type="button" disabled>导出 Markdown</button><button id="export-csv" class="export-btn" type="button" disabled>导出 CSV</button></div></div>"""
        html = html.replace("</section>", toolbar + "</section>", 1)
        html = html.replace("</body>", '<script src="/user_explanation.js"></script><script src="/export_tools_v2.js"></script></body>', 1)
        return html.encode("utf-8")

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self.send_bytes(self._page(), "text/html; charset=utf-8")
            return
        assets = {
            "/user_explanation.js": ("user_explanation.js", "text/javascript; charset=utf-8"),
            "/export_tools_v2.js": ("export_tools_v2.js", "text/javascript; charset=utf-8"),
            "/export_tools.css": ("export_tools.css", "text/css; charset=utf-8"),
        }
        if self.path in assets:
            filename, content_type = assets[self.path]
            self.send_bytes((PROJECT_DIR / "static" / filename).read_bytes(), content_type)
            return
        if self.path == "/api/config":
            self.send_json({"enabled": is_configured(), "provider": "DeepSeek", "model": MODEL, "features": ["new", "append", "explain", "export"]})
            return
        if self.path == "/api/health":
            self.send_json({"status": "ok", "version": 5})
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
                raise ValueError("请输入需求或问题")
            mode = body.get("mode", "new")
            schedule = body.get("current_schedule") or []
            request = body.get("current_request") or {}
            if mode == "new":
                result = run_new_schedule(text)
            elif mode == "append":
                result = run_revision(text, schedule, request)
            elif mode == "explain":
                result = run_explanation(text, schedule)
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
    print("功能：从0排表 / 追加需求 / 用户解释 / 文件导出")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
