from __future__ import annotations

import json
from typing import Any

from deepseek_client import MODEL, _structured_call


USER_EXPLANATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sentences": {
            "type": "array",
            "items": {"type": "string"},
        },
        "read_only_confirmation": {"type": "boolean"},
    },
    "required": ["sentences", "read_only_confirmation"],
}


USER_EXPLANATION_INSTRUCTIONS = """你是门店排班结果的用户解释助手，只负责解释，不得修改排班。

输出要求：
1. 只输出面向普通门店用户的简短中文句子，不要解释程序如何运行。
2. 不得出现：LLM、AI、Python、算法、模型、提示词、校验器、JSON、R-01等规则编号、系统内部、约束求解。
3. 优先使用这些句式：
   - “因为 E01 偏好早班，所以安排在周一早班。”
   - “虽然 E07 偏好晚班，但当班人手不足，因此安排在周三早班。”
   - “E04 周一不可工作，因此当天没有安排 E04。”
   - “E06 周二请假，因此周二没有安排 E06。”
4. 每句话只解释一个原因，尽量不超过45个汉字。
5. 必须引用当前排班和员工数据中的真实员工ID、日期、班次、偏好、技能或请假信息，不得猜测。
6. 只有数据确实支持时，才能说“人手不足”或“没有足够员工”。
7. 用户问整体安排时，选择最有代表性的4至8句话；用户问具体员工或班次时，只回答相关内容。
8. 如果用户要求修改排班，只回复“如需调整排班，请切换到追加需求模式。”，不得给出修改结果。
9. read_only_confirmation 必须为 true。
"""


def explain_for_user(
    *,
    question: str,
    schedule: list[dict[str, Any]],
    employees: list[dict[str, Any]],
    changes: list[str] | None = None,
) -> dict[str, Any]:
    input_payload = {
        "用户问题": question,
        "当前排班": [
            {"day": item["day"], "shift": item["shift"], "employees": item["employees"]}
            for item in schedule
        ],
        "员工数据": [
            {
                "id": employee["id"],
                "skills": employee["skills"],
                "available_days": employee["available_days"],
                "leave_days": employee["leave_days"],
                "preferred_shift": employee.get("preferred_shift"),
            }
            for employee in employees
        ],
        "本次排班改动": changes or [],
    }
    result = _structured_call(
        instructions=USER_EXPLANATION_INSTRUCTIONS,
        input_text=json.dumps(input_payload, ensure_ascii=False),
        schema_name="user_facing_schedule_explanation",
        schema=USER_EXPLANATION_SCHEMA,
        max_output_tokens=1200,
        timeout=60,
    )
    result["model"] = MODEL
    result["read_only_confirmation"] = True
    return result
