from __future__ import annotations

import json
import sys
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_DIR = HERE.parent
sys.path.insert(0, str(PROJECT_DIR))

from deepseek_client import (  # noqa: E402
    DeepSeekError,
    MODEL,
    interpret,
    is_configured,
    revise_schedule,
)
from scheduler import (  # noqa: E402
    DAYS,
    SHIFTS,
    SHIFT_TIMES,
    generate_schedule,
    load_employees,
    validate_schedule,
)


HOST = "127.0.0.1"
PORT = 8000


def to_scheduler_text(parsed: dict) -> str:
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


def run_new_schedule(user_text: str) -> dict:
    try:
        understanding = interpret(user_text)
    except DeepSeekError as error:
        result = generate_schedule(user_text)
        result["mode"] = "new"
        result["agent"] = {
            "source": "local_fallback",
            "model": None,
            "understanding": "DeepSeek 不可用，已使用本地解析保证 Demo 可继续。",
            "warning": str(error),
        }
        return result
    if understanding.get("needs_clarification"):
        return {
            "success": False,
            "mode": "new",
            "needs_clarification": True,
            "clarification_question": understanding.get("clarification_question"),
            "agent": {
                "source": "llm",
                "model": MODEL,
                "understanding": understanding.get("understanding"),
            },
        }
    result = generate_schedule(to_scheduler_text(understanding))
    result["mode"] = "new"
    result["request"]["original_text"] = user_text
    result["request"]["deepseek_interpretation"] = understanding
    result["agent"] = {
        "source": "llm",
        "provider": "DeepSeek",
        "model": MODEL,
        "understanding": understanding.get("understanding"),
        "fallback": False,
    }
    return result


def _plain_schedule(schedule: list[dict]) -> list[dict]:
    return [
        {
            "day": item["day"],
            "shift": item["shift"],
            "employees": list(dict.fromkeys(item["employees"])),
        }
        for item in schedule
    ]


def _enrich_schedule(schedule: list[dict], employees: list[dict]) -> list[dict]:
    employee_by_id = {employee["id"]: employee for employee in employees}
    enriched = []
    for item in schedule:
        team = [employee_by_id[eid] for eid in item["employees"] if eid in employee_by_id]
        enriched.append(
            {
                "day": item["day"],
                "shift": item["shift"],
                "time": SHIFT_TIMES[item["shift"]],
                "employees": item["employees"],
                "employee_details": [
                    {
                        "id": employee["id"],
                        "position": employee["position"],
                        "skills": employee["skills"],
                    }
                    for employee in team
                ],
                "coverage": {
                    "店长值守": sum("店长值守" in employee["skills"] for employee in team),
                    "饮品制作": sum("饮品制作" in employee["skills"] for employee in team),
                    "收银": sum("收银" in employee["skills"] for employee in team),
                },
            }
        )
    return enriched


def _diff_schedule(before: list[dict], after: list[dict]) -> list[str]:
    old = {(item["day"], item["shift"]): set(item["employees"]) for item in before}
    new = {(item["day"], item["shift"]): set(item["employees"]) for item in after}
    changes = []
    for key in sorted(new, key=lambda value: (DAYS.index(value[0]), SHIFTS.index(value[1]))):
        added = sorted(new[key] - old.get(key, set()))
        removed = sorted(old.get(key, set()) - new[key])
        pieces = []
        if added:
            pieces.append("增加 " + "、".join(added))
        if removed:
            pieces.append("移除 " + "、".join(removed))
        if pieces:
            changes.append(f"{key[0]}{key[1]}：" + "；".join(pieces))
    return changes or ["现有排班已经满足追加需求，无需调整。"]


def run_revision(user_text: str, current_schedule: list[dict], current_request: dict) -> dict:
    if not current_schedule:
        return {
            "success": False,
            "mode": "append",
            "needs_base_schedule": True,
            "error": "追加需求前需要先生成一张排班表。",
        }
    employees = load_employees()
    base_schedule = _plain_schedule(current_schedule)
    expected_keys = {(item["day"], item["shift"]) for item in base_schedule}
    request = {
        "days": current_request.get("days") or [day for day in DAYS if any(x["day"] == day for x in base_schedule)],
        "shifts": current_request.get("shifts") or [shift for shift in SHIFTS if any(x["shift"] == shift for x in base_schedule)],
    }
    feedback: list[dict[str, str]] = []
    last_validation = None
    last_error = "修订结果未通过规则校验"
    last_revision = None

    for _ in range(2):
        try:
            revision = revise_schedule(user_text, base_schedule, employees, feedback)
        except DeepSeekError as error:
            return {
                "success": False,
                "mode": "append",
                "preserve_current": True,
                "error": str(error),
                "agent": {
                    "source": "deepseek",
                    "model": MODEL,
                    "understanding": "追加需求需要 DeepSeek 修改现有排班，本次未修改原表。",
                },
            }
        last_revision = revision
        if revision.get("needs_clarification"):
            return {
                "success": False,
                "mode": "append",
                "needs_clarification": True,
                "preserve_current": True,
                "clarification_question": revision.get("clarification_question"),
                "agent": {
                    "source": "llm",
                    "model": MODEL,
                    "understanding": revision.get("understanding"),
                },
            }
        proposed = _plain_schedule(revision.get("schedule") or [])
        proposed_keys = {(item["day"], item["shift"]) for item in proposed}
        key_feedback = []
        if proposed_keys != expected_keys:
            key_feedback.append(
                {
                    "rule": "班次集合",
                    "message": "必须完整保留现有排班的日期和班次，不能新增或删除班次。",
                }
            )
        last_validation = validate_schedule(proposed, employees, request)
        feedback = key_feedback + last_validation["violations"]
        if not revision.get("requirement_satisfied", False):
            feedback.append(
                {
                    "rule": "追加需求",
                    "message": revision.get("requirement_evidence") or "追加需求尚未满足",
                }
            )
        if not feedback:
            counts = Counter(eid for item in proposed for eid in item["employees"])
            return {
                "success": True,
                "mode": "append",
                "request": current_request,
                "schedule": _enrich_schedule(proposed, employees),
                "validation": last_validation,
                "statistics": {
                    "total_shifts": len(proposed),
                    "total_assignments": sum(len(item["employees"]) for item in proposed),
                    "employee_shift_counts": dict(sorted(counts.items())),
                },
                "changes": _diff_schedule(base_schedule, proposed),
                "requirement_evidence": revision.get("requirement_evidence"),
                "agent": {
                    "source": "llm",
                    "provider": "DeepSeek",
                    "model": MODEL,
                    "understanding": revision.get("understanding"),
                    "fallback": False,
                },
            }
        last_error = "；".join(item["message"] for item in feedback[:4])

    return {
        "success": False,
        "mode": "append",
        "preserve_current": True,
        "error": last_error,
        "validation": last_validation,
        "agent": {
            "source": "llm",
            "model": MODEL,
            "understanding": (last_revision or {}).get("understanding", "修订未通过校验，原表保持不变。"),
        },
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DeepSeekSchedulerAgent/2.0"

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
            self.send_bytes((PROJECT_DIR / "static" / "agent.html").read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/api/config":
            self.send_json({"enabled": is_configured(), "provider": "DeepSeek", "model": MODEL, "base_url": "https://api.deepseek.com"})
            return
        if self.path == "/api/health":
            self.send_json({"status": "ok", "deepseek_configured": is_configured()})
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
                raise ValueError("请输入自然语言排班需求")
            mode = body.get("mode", "new")
            if mode == "append":
                result = run_revision(text, body.get("current_schedule") or [], body.get("current_request") or {})
            elif mode == "new":
                result = run_new_schedule(text)
            else:
                raise ValueError("不支持的排班模式")
            self.send_json(result)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.send_json({"error": "Agent 处理失败", "detail": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"DeepSeek V4.1 Flash 排班 Agent：http://{HOST}:{PORT}")
    print("模型：deepseek-flash")
    print("状态：" + ("API Key 已配置" if is_configured() else "未配置 Key，将使用本地降级模式"))
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
