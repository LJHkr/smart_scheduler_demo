from __future__ import annotations

import json
from typing import Any

from deepseek_client import MODEL, _structured_call


EXPLANATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "key_reasons": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "detail", "evidence"],
            },
        },
        "tradeoffs": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "read_only_confirmation": {"type": "boolean"},
    },
    "required": ["answer", "key_reasons", "tradeoffs", "limitations", "read_only_confirmation"],
}


EXPLANATION_INSTRUCTIONS = """你是智能排班 Agent 的只读解释器。
你只能基于用户提供的当前排班、员工数据、硬规则和问题进行解释，绝对不能修改排班表。
回答要说明结论和可核对证据，不输出隐藏思维过程，不编造员工技能、可用日期或业务背景。
优先解释：硬规则为什么满足、关键岗位为什么这样覆盖、员工偏好与公平性的取舍、追加修改为什么必要。
证据尽量包含具体日期、班次和员工 ID。
如果用户实际上要求改表，明确告诉用户切换到“追加需求”模式；本次仍不得返回修改后的排班。
如果信息不足，要在 limitations 中说明，不能猜测。
read_only_confirmation 必须为 true。
"""


def explain_schedule(
    *,
    question: str,
    schedule: list[dict[str, Any]],
    employees: list[dict[str, Any]],
    request: dict[str, Any] | None = None,
    changes: list[str] | None = None,
) -> dict[str, Any]:
    compact_schedule = [
        {"day": item["day"], "shift": item["shift"], "employees": item["employees"]}
        for item in schedule
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
    input_payload = {
        "用户问题": question,
        "当前排班": compact_schedule,
        "员工数据": compact_employees,
        "原始排班请求": request or {},
        "上一版到当前版的改动": changes or [],
        "硬规则": [
            "R-01 每班至少1名店长值守",
            "R-02 每班至少2名饮品制作",
            "R-03 每班至少1名收银",
            "R-04 工作日每班至少4人，周末每班至少6人",
            "R-05 每人每天最多1班、每周最多5班",
            "R-06 不得连续工作超过5天",
            "R-07 晚班后不得接次日早班",
            "R-08 请假和不可工作日期不得排班",
            "R-09 不得自行补充技能",
        ],
    }
    result = _structured_call(
        instructions=EXPLANATION_INSTRUCTIONS,
        input_text=json.dumps(input_payload, ensure_ascii=False),
        schema_name="schedule_explanation",
        schema=EXPLANATION_SCHEMA,
        max_output_tokens=2500,
        timeout=60,
    )
    result["model"] = MODEL
    result["read_only_confirmation"] = True
    return result
