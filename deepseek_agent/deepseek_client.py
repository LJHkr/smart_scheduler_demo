from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from llm_client import REQUEST_SCHEMA, SYSTEM_INSTRUCTIONS


BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / "deepseek_key.txt"
API_URL = "https://api.deepseek.com/responses"
MODEL = "deepseek-flash"


class DeepSeekError(RuntimeError):
    pass


def read_api_key() -> str:
    if not KEY_FILE.exists():
        raise DeepSeekError("尚未配置 DeepSeek API Key")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key or "粘贴" in key or "your_" in key.lower():
        raise DeepSeekError("deepseek_key.txt 中没有有效的 API Key")
    if "\n" in key or "\r" in key:
        raise DeepSeekError("API Key 文件只能包含一行密钥")
    return key


def is_configured() -> bool:
    try:
        read_api_key()
        return True
    except DeepSeekError:
        return False


def _extract_output_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise DeepSeekError("DeepSeek 响应中没有可用文本")
    return "".join(texts)


def _structured_call(
    *,
    instructions: str,
    input_text: str,
    schema_name: str,
    schema: dict[str, Any],
    max_output_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "instructions": instructions,
        "input": input_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
            }
        },
        "temperature": 0.2,
        "max_output_tokens": max_output_tokens,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise DeepSeekError(f"DeepSeek API 返回 HTTP {error.code}：{detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise DeepSeekError(f"无法连接 DeepSeek API：{error}") from error
    try:
        return json.loads(_extract_output_text(response_data))
    except json.JSONDecodeError as error:
        raise DeepSeekError("DeepSeek 未返回合法 JSON") from error


def interpret(user_text: str) -> dict[str, Any]:
    parsed = _structured_call(
        instructions=SYSTEM_INSTRUCTIONS,
        input_text=user_text,
        schema_name="schedule_request",
        schema=REQUEST_SCHEMA,
        max_output_tokens=1000,
        timeout=40,
    )
    parsed["original_text"] = user_text
    parsed["source"] = "deepseek"
    parsed["model"] = MODEL
    return parsed


REVISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "understanding": {"type": "string"},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": "string"},
        "requirement_satisfied": {"type": "boolean"},
        "requirement_evidence": {"type": "string"},
        "schedule": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "day": {
                        "type": "string",
                        "enum": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                    },
                    "shift": {"type": "string", "enum": ["早班", "晚班"]},
                    "employees": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "pattern": "^E(0[1-9]|1[0-9]|20)$",
                        },
                    },
                },
                "required": ["day", "shift", "employees"],
            },
        },
        "change_summary": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "understanding",
        "needs_clarification",
        "clarification_question",
        "requirement_satisfied",
        "requirement_evidence",
        "schedule",
        "change_summary",
    ],
}


def revise_schedule(
    user_text: str,
    current_schedule: list[dict[str, Any]],
    employees: list[dict[str, Any]],
    validation_feedback: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    compact_schedule = [
        {"day": item["day"], "shift": item["shift"], "employees": item["employees"]}
        for item in current_schedule
    ]
    compact_employees = [
        {
            "id": employee["id"],
            "position": employee["position"],
            "skills": employee["skills"],
            "available_days": employee["available_days"],
            "leave_days": employee["leave_days"],
            "preferred_shift": employee.get("preferred_shift"),
        }
        for employee in employees
    ]
    instructions = """你是排班表修订 Agent。用户会提供当前排班和一条追加需求。
在当前排班基础上做最少量调整，不要从零生成完全不同的表。
必须保留原表的日期和班次集合，不能增加或删除班次；schedule 返回全部班次，不是只返回改动。
只能使用员工数据中已有的 ID、技能、可工作日期、请假和偏好。
修订后必须满足：每班至少1名店长值守、2名饮品制作、1名收银；工作日每班至少4人，周末每班至少6人；每人每天最多1班、每周最多5班；不得连续工作超过5天；晚班后不得接次日早班；请假或不可工作日期不得排班。
优先满足追加需求，其次最小化相对原表的人员增删。
如果需求含糊、与硬规则冲突或无法确认，needs_clarification=true，不要猜测。
如果提供了上次校验错误，必须修复后再返回。
"""
    input_payload = {
        "追加需求": user_text,
        "当前排班": compact_schedule,
        "员工数据": compact_employees,
        "上次校验错误": validation_feedback or [],
    }
    return _structured_call(
        instructions=instructions,
        input_text=json.dumps(input_payload, ensure_ascii=False),
        schema_name="schedule_revision",
        schema=REVISION_SCHEMA,
        max_output_tokens=5000,
        timeout=60,
    )
