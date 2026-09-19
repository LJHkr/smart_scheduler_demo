from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SHIFTS = ["早班", "晚班"]


class LLMClientError(RuntimeError):
    pass


def load_env_file(path: Path | None = None) -> None:
    """安全读取简单 KEY=VALUE；不展开变量，也不执行命令替换。"""
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line_number, raw_line in enumerate(env_path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise LLMClientError(f".env 第 {line_number} 行格式错误")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise LLMClientError(f".env 第 {line_number} 行变量名无效")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def get_llm_config() -> dict[str, Any]:
    load_env_file()
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-5-mini")
    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    return {
        "enabled": bool(api_key),
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "timeout": timeout,
    }


REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["generate_schedule", "unknown"],
        },
        "days": {
            "type": "array",
            "items": {"type": "string", "enum": DAYS},
        },
        "shifts": {
            "type": "array",
            "items": {"type": "string", "enum": SHIFTS},
        },
        "respect_preferences": {"type": "boolean"},
        "balance_workload": {"type": "boolean"},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": "string"},
        "understanding": {"type": "string"},
    },
    "required": [
        "intent",
        "days",
        "shifts",
        "respect_preferences",
        "balance_workload",
        "needs_clarification",
        "clarification_question",
        "understanding",
    ],
}


SYSTEM_INSTRUCTIONS = """你是连锁门店智能排班 Agent 的需求理解模块。
你的唯一任务是把用户的中文自然语言转换成给定 JSON Schema。

业务事实：
- 一周为周一至周日，班次只有早班和晚班。
- 未指定日期时默认整周；未指定班次时默认早班和晚班。
- “工作日”表示周一至周五，“周末”表示周六和周日。
- 员工偏好和工作量均衡都是软目标；用户没有明确取消时均设为 true。
- 不得虚构日期、班次、员工、技能或规则。
- 当前基础版只支持选择日期、班次、是否照顾偏好和是否均衡工作量。
- 如果用户要求修改人数、技能、请假、指定/排除员工或其他尚不支持的约束，needs_clarification=true，说明基础版暂不支持，并提出一个简短问题。
- 如果请求与排班无关，intent=unknown 且 needs_clarification=true。
- clarification_question 在不需要追问时必须为空字符串。
- understanding 用一句简洁中文复述系统对需求的理解。
"""


def _extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    texts: list[str] = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                texts.append(content["text"])
    if not texts:
        raise LLMClientError("LLM 响应中没有可用文本")
    return "".join(texts)


def interpret_with_llm(user_text: str) -> dict[str, Any]:
    config = get_llm_config()
    if not config["enabled"]:
        raise LLMClientError("未配置 LLM_API_KEY 或 OPENAI_API_KEY")

    payload = {
        "model": config["model"],
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": user_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "schedule_request",
                "description": "结构化的排班请求",
                "strict": True,
                "schema": REQUEST_SCHEMA,
            }
        },
        "store": False,
    }
    request = urllib.request.Request(
        f"{config['base_url']}/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LLMClientError(f"LLM API 返回 HTTP {error.code}：{detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise LLMClientError(f"无法连接 LLM API：{error}") from error

    try:
        parsed = json.loads(_extract_output_text(response_data))
    except json.JSONDecodeError as error:
        raise LLMClientError("LLM 未返回合法 JSON") from error

    if not parsed.get("days"):
        parsed["days"] = DAYS[:]
    if not parsed.get("shifts"):
        parsed["shifts"] = SHIFTS[:]
    parsed["original_text"] = user_text
    parsed["source"] = "llm"
    parsed["model"] = config["model"]
    return parsed


def public_llm_status() -> dict[str, Any]:
    config = get_llm_config()
    return {
        "enabled": config["enabled"],
        "model": config["model"],
        "base_url": config["base_url"],
    }
