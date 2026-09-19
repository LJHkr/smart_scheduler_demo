# 智能排班 Agent

DeepSeek 负责理解自然语言、提出排班修改建议和生成用户可读的安排说明；Python 负责生成并检查排班。

## 启动

```powershell
python main.py
```

首次启动时粘贴 DeepSeek API Key，然后访问 <http://127.0.0.1:8000>。

## 功能

### 从 0 排表

根据自然语言生成全新排班。

### 追加需求

在当前排班上做最少量调整。新版本检查通过后才会替换原表，否则保留原表。

### 解释 / 提问

解释只面向普通门店用户，只输出员工安排原因，例如：

- “因为 E01 偏好早班，所以安排在周一早班。”
- “虽然 E07 偏好晚班，但当班人手不足，因此安排在周三早班。”
- “E06 周二请假，因此周二没有安排 E06。”
- “E04 周一不可工作，因此当天没有安排 E04。”

解释中不会展示模型、算法、程序、提示词、JSON、规则编号或内部运行过程。只有数据确实支持时，才会说明“人手不足”。

解释模式是只读的。如果用户要求改表，系统会提示切换到“追加需求”，当前排班保持不变。

### 文件导出

- **Markdown**：排班表、改动记录、用户安排说明、检查结果和 AI 使用记录。
- **CSV**：日期、班次、员工、岗位、人数及技能覆盖，适合飞书表格或 Excel。

导出只读取当前版本，不会重新排班。

## 项目结构

```text
smart_scheduler_demo/
├── main.py                              # 唯一入口
├── scheduler.py                         # 排班生成与检查
├── data/
│   ├── employees.json
│   └── rules.json
├── static/
│   ├── agent_v3.html
│   ├── user_explanation.js              # 用户解释界面
│   ├── export_tools_v2.js
│   └── export_tools.css
├── deepseek_agent/
│   ├── deepseek_app.py                  # 新建与追加排班
│   ├── deepseek_app_v5.py               # 正式服务入口
│   ├── deepseek_client.py
│   └── explanation_client_v2.py         # 用户解释生成
├── tests/
├── 排班规则.md
├── 员工名单.md
└── legacy/
```

## 测试

```powershell
python -m unittest discover -s tests -v
node --check static\user_explanation.js
node --check static\export_tools_v2.js
```

当前 12 个测试覆盖排班、追加需求、只读解释、用户话术和文件导出。

## AI 工具使用记录

- DeepSeek 用于理解用户需求、生成调整建议和安排说明。
- 排班结果由程序检查后再展示。
- 员工数据来自题目材料，正式提交前应由团队人工复核。
