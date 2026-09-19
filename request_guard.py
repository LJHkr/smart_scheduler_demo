from __future__ import annotations

import re


def detect_underdetermined_request(text: str) -> dict | None:
    """识别必须依赖题目未提供数据、因而不能擅自判断的请求。"""
    normalized = (text or "").strip()
    cases = [
        (
            r"客流|业务量|订单量|高峰|低峰",
            "题目没有提供各日期、各班次的客流量或业务量数据",
            "请补充各日期、各班次的客流预测，或直接给出每班目标人数。",
            ["分日期、分班次的客流或业务量", "客流与目标人数的换算标准"],
        ),
        (
            r"最优秀|表现最好|绩效最高|能力最强|效率最高|排名最高",
            "员工数据中没有绩效、效率或能力排名",
            "请补充员工评价数据，或说明“优秀”的判断标准。",
            ["员工绩效或效率数据", "优秀员工的评价标准"],
        ),
        (
            r"工资最低|成本最低|人工成本|薪资|时薪",
            "员工数据中没有工资、时薪或用工成本",
            "请补充员工成本数据，或取消成本优化要求。",
            ["员工工资或时薪", "成本优化口径"],
        ),
    ]
    for pattern, reason, question, missing_data in cases:
        if re.search(pattern, normalized):
            return {
                "unable_to_determine": True,
                "reason": reason,
                "clarification_question": f"无法判断：{reason}。{question}",
                "missing_data": missing_data,
            }
    return None
