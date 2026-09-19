# 智能排班助手基础 Demo

这是一个仅依赖 Python 标准库的 Web Demo。用户输入自然语言需求后，系统读取 E01～E20 员工数据，生成排班，并独立校验 R-01～R-09。

## 运行

需要 Python 3.10 或更高版本。

```bash
cd smart_scheduler_demo
python app.py
```

浏览器访问：<http://127.0.0.1:8000>

## 测试

```bash
python -m unittest discover -s tests -v
```

## 当前能力

- 识别完整一周、工作日、周末及单独星期需求
- 识别“只排早班”和“只排晚班”
- 根据员工技能、可工作日期、请假和偏好生成排班
- 校验店长值守、饮品制作、收银和最低人数
- 校验每周最多 5 班、每天最多 1 班、连续工作和晚班接早班
- 无法生成合规排班时返回冲突，不伪造结果

## 架构说明

1. `app.py`：Python Web Server 与 JSON API。
2. `scheduler.py`：请求解析、排班生成、独立规则校验和结果解释。
3. `data/employees.json`：纸质题目转录的员工数据。
4. `static/index.html`：无需前端框架的演示页面。
5. `tests/test_scheduler.py`：正常、解析和违规检测用例。

## AI 工具使用记录参考

- AI 辅助生成了基础 Web Server、排班算法、规则校验器、页面和测试代码。
- 员工数据来自题目图片的人工转录，并应由团队再次对照纸质材料复核。
- 排班结果不直接信任生成器，而是由独立校验函数逐条检查 R-01～R-09。
