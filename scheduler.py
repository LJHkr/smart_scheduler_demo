from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SHIFTS = ["早班", "晚班"]
SHIFT_TIMES = {"早班": "09:00–17:00", "晚班": "13:00–21:00"}


def load_employees() -> list[dict[str, Any]]:
    with (BASE_DIR / "data" / "employees.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_request(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    days = DAYS[:]
    if "周末" in text:
        days = ["周六", "周日"]
    elif "工作日" in text or "周一至周五" in text or "周一到周五" in text:
        days = DAYS[:5]
    elif not any(word in text for word in ("全周", "整周", "一周", "下周", "完整")):
        mentioned = [day for day in DAYS if day in text]
        if mentioned:
            days = mentioned

    shifts = SHIFTS[:]
    if "只排早班" in text:
        shifts = ["早班"]
    elif "只排晚班" in text:
        shifts = ["晚班"]

    return {
        "original_text": text or "请生成下周完整排班，并尽量满足员工偏好",
        "days": days,
        "shifts": shifts,
        "respect_preferences": "不考虑偏好" not in text,
        "balance_workload": "不需要均衡" not in text,
    }


def _required_headcount(day: str) -> int:
    return 6 if day in ("周六", "周日") else 4


def _would_exceed_consecutive(worked_days: set[int], day_index: int) -> bool:
    candidate = set(worked_days)
    candidate.add(day_index)
    run = 0
    for index in range(len(DAYS)):
        if index in candidate:
            run += 1
            if run > 5:
                return True
        else:
            run = 0
    return False


def _generate_once(
    employees: list[dict[str, Any]], request: dict[str, Any], rng: random.Random
) -> tuple[list[dict[str, Any]], str | None]:
    assignments: list[dict[str, Any]] = []
    weekly_count: Counter[str] = Counter()
    worked_days: dict[str, set[int]] = defaultdict(set)
    assigned_shift: dict[tuple[str, int], str] = {}

    employee_by_id = {employee["id"]: employee for employee in employees}

    def eligible(employee: dict[str, Any], day: str, shift: str) -> bool:
        employee_id = employee["id"]
        day_index = DAYS.index(day)
        if day not in employee["available_days"] or day in employee["leave_days"]:
            return False
        if weekly_count[employee_id] >= 5:
            return False
        if (employee_id, day_index) in assigned_shift:
            return False
        if shift == "早班" and day_index > 0:
            if assigned_shift.get((employee_id, day_index - 1)) == "晚班":
                return False
        if _would_exceed_consecutive(worked_days[employee_id], day_index):
            return False
        return True

    def score(employee: dict[str, Any], shift: str, required_skill: str | None) -> float:
        employee_id = employee["id"]
        value = weekly_count[employee_id] * 14
        if request["respect_preferences"]:
            preference = employee.get("preferred_shift")
            if preference == shift:
                value -= 5
            elif preference and preference != shift:
                value += 4
        if required_skill and required_skill in employee["skills"]:
            value -= 1
        value += rng.random() * 3
        return value

    for day in request["days"]:
        day_index = DAYS.index(day)
        for shift in request["shifts"]:
            team: list[str] = []

            def add_best(required_skill: str | None = None) -> bool:
                candidates = [
                    employee
                    for employee in employees
                    if employee["id"] not in team
                    and eligible(employee, day, shift)
                    and (required_skill is None or required_skill in employee["skills"])
                ]
                if not candidates:
                    return False
                candidates.sort(key=lambda employee: score(employee, shift, required_skill))
                pool = candidates[: min(3, len(candidates))]
                chosen = rng.choice(pool)
                team.append(chosen["id"])
                return True

            if not add_best("店长值守"):
                return assignments, f"{day}{shift}缺少可用的店长值守人员"

            while sum("饮品制作" in employee_by_id[eid]["skills"] for eid in team) < 2:
                if not add_best("饮品制作"):
                    return assignments, f"{day}{shift}缺少饮品制作人员"

            while sum("收银" in employee_by_id[eid]["skills"] for eid in team) < 1:
                if not add_best("收银"):
                    return assignments, f"{day}{shift}缺少收银人员"

            target = _required_headcount(day)
            while len(team) < target:
                if not add_best():
                    return assignments, f"{day}{shift}无法满足最低人数 {target} 人"

            for employee_id in team:
                weekly_count[employee_id] += 1
                worked_days[employee_id].add(day_index)
                assigned_shift[(employee_id, day_index)] = shift

            assignments.append(
                {
                    "day": day,
                    "shift": shift,
                    "time": SHIFT_TIMES[shift],
                    "employees": team,
                }
            )

    return assignments, None


def validate_schedule(
    assignments: list[dict[str, Any]],
    employees: list[dict[str, Any]],
    request: dict[str, Any],
) -> dict[str, Any]:
    employee_by_id = {employee["id"]: employee for employee in employees}
    violations: list[dict[str, str]] = []
    weekly_count: Counter[str] = Counter()
    daily_shifts: dict[tuple[str, str], list[str]] = defaultdict(list)
    worked_days: dict[str, set[int]] = defaultdict(set)

    def fail(rule: str, message: str) -> None:
        violations.append({"rule": rule, "message": message})

    assignment_map = {(item["day"], item["shift"]): item for item in assignments}
    for day in request["days"]:
        for shift in request["shifts"]:
            if (day, shift) not in assignment_map:
                fail("R-04", f"缺少班次：{day}{shift}")

    for item in assignments:
        day, shift = item["day"], item["shift"]
        employee_ids = item["employees"]
        label = f"{day}{shift}"
        if len(employee_ids) != len(set(employee_ids)):
            fail("R-08", f"{label}存在重复员工")
        known = [employee_by_id[eid] for eid in employee_ids if eid in employee_by_id]
        unknown = [eid for eid in employee_ids if eid not in employee_by_id]
        if unknown:
            fail("R-09", f"{label}包含未知员工：{', '.join(unknown)}")
        if not any("店长值守" in employee["skills"] for employee in known):
            fail("R-01", f"{label}缺少店长值守人员")
        if sum("饮品制作" in employee["skills"] for employee in known) < 2:
            fail("R-02", f"{label}饮品制作人员少于2人")
        if not any("收银" in employee["skills"] for employee in known):
            fail("R-03", f"{label}缺少收银人员")
        minimum = _required_headcount(day)
        if len(employee_ids) < minimum:
            fail("R-04", f"{label}仅{len(employee_ids)}人，至少需要{minimum}人")

        for employee in known:
            employee_id = employee["id"]
            if day not in employee["available_days"]:
                fail("R-08", f"{employee_id}在{day}不可工作")
            if day in employee["leave_days"]:
                fail("R-08", f"{employee_id}在{day}请假")
            weekly_count[employee_id] += 1
            daily_shifts[(employee_id, day)].append(shift)
            worked_days[employee_id].add(DAYS.index(day))

    for employee_id, count in weekly_count.items():
        if count > 5:
            fail("R-05", f"{employee_id}本周安排{count}班，超过5班")
    for (employee_id, day), shifts in daily_shifts.items():
        if len(shifts) > 1:
            fail("R-05", f"{employee_id}在{day}被安排多个班次")
    for employee_id, indexes in worked_days.items():
        run = 0
        for index in range(len(DAYS)):
            run = run + 1 if index in indexes else 0
            if run > 5:
                fail("R-06", f"{employee_id}连续工作超过5天")
                break
        for index in range(len(DAYS) - 1):
            current = daily_shifts.get((employee_id, DAYS[index]), [])
            following = daily_shifts.get((employee_id, DAYS[index + 1]), [])
            if "晚班" in current and "早班" in following:
                fail("R-07", f"{employee_id}在{DAYS[index]}晚班后接{DAYS[index + 1]}早班")

    rules = {}
    for rule in [f"R-{index:02d}" for index in range(1, 10)]:
        rule_violations = [item["message"] for item in violations if item["rule"] == rule]
        rules[rule] = {"passed": not rule_violations, "messages": rule_violations}

    return {"valid": not violations, "rules": rules, "violations": violations}


def _enrich(assignments: list[dict[str, Any]], employees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    employee_by_id = {employee["id"]: employee for employee in employees}
    result = []
    for item in assignments:
        team = [employee_by_id[eid] for eid in item["employees"]]
        enriched = dict(item)
        enriched["employee_details"] = [
            {"id": employee["id"], "position": employee["position"], "skills": employee["skills"]}
            for employee in team
        ]
        enriched["coverage"] = {
            "店长值守": sum("店长值守" in employee["skills"] for employee in team),
            "饮品制作": sum("饮品制作" in employee["skills"] for employee in team),
            "收银": sum("收银" in employee["skills"] for employee in team),
        }
        result.append(enriched)
    return result


def generate_schedule(text: str) -> dict[str, Any]:
    employees = load_employees()
    request = parse_request(text)
    best_assignments: list[dict[str, Any]] = []
    last_error = "未找到满足全部条件的方案"

    seed = sum(ord(char) for char in request["original_text"])
    for attempt in range(1200):
        assignments, error = _generate_once(employees, request, random.Random(seed + attempt * 7919))
        if len(assignments) > len(best_assignments):
            best_assignments = assignments
        if error is None:
            validation = validate_schedule(assignments, employees, request)
            if validation["valid"]:
                counts = Counter(eid for item in assignments for eid in item["employees"])
                return {
                    "success": True,
                    "request": request,
                    "schedule": _enrich(assignments, employees),
                    "validation": validation,
                    "statistics": {
                        "total_shifts": len(assignments),
                        "total_assignments": sum(len(item["employees"]) for item in assignments),
                        "employee_shift_counts": dict(sorted(counts.items())),
                    },
                }
        else:
            last_error = error

    validation = validate_schedule(best_assignments, employees, request)
    return {
        "success": False,
        "request": request,
        "schedule": _enrich(best_assignments, employees),
        "validation": validation,
        "error": last_error,
        "suggestion": "请减少附加限制，或补充具备对应技能且可工作的员工。",
    }
