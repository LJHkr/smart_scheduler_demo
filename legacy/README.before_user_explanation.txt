# 智能排班 Agent（DSAgent）

DeepSeek V4.1 Flash 负责理解、修订建议和解释；Python 负责生成并校验排班。系统支持从 0 排表、追加需求、只读解释，以及 Markdown/CSV 文件导出。

## 启动

需要 Python 3.10 或更高版本。在项目目录运行唯一入口：

```powershell
python main.py
```

首次启动时粘贴 DeepSeek API Key，然后访问 <http://127.0.0.1:8000>。

Key 只保存在本机 `deepseek_agent/deepseek_key.txt`。API 地址和模型已经固定：

- API：`https://api.deepseek.com/responses`
- 模型：`deepseek-flash`

## 功能

### 从 0 排表

根据自然语言生成全新排班，并自动解释硬规则、关键岗位、偏好及工作量取舍。

### 追加需求

在当前排班上做最少量修改。修订结果必须重新通过 R-01～R-09；失败时保留原表。

### 解释 / 提问

只读取当前排班并回答问题，不修改表格。如果用户提出改表要求，Agent 会提示切换到“追加需求”。

### 文件导出

生成排班后，页面底部会启用两个按钮：

- **导出 Markdown**：包含用户需求、排班表、版本改动、R-01～R-09 校验、LLM 安排解释及 AI 工具使用记录，适合复制到飞书文档。
- **导出 CSV**：包含日期、班次、时间、员工、人数、技能覆盖及校验结果，使用 UTF-8 BOM，适合 Excel、飞书表格或数据复核。

导出使用浏览器当前版本，不会重新调用 LLM，也不会改变排班。

## 示例

- 新建：“生成下周完整排班，尽量照顾员工偏好。”
- 追加：“周三不要安排 E07，其他班次尽量不变。”
- 解释：“为什么周三早班安排这些人？”

## 架构

```text
用户自然语言
  ├─ 从 0 排表 → DeepSeek 意图解析 → Python 排班器
  ├─ 追加需求   → 当前排班 + DeepSeek 最小修订
  └─ 解释/提问  → 当前排班 + DeepSeek 只读解释
                                  ↓
                         R-01～R-09 独立校验
                                  ↓
                         Markdown / CSV 导出
```

## 项目结构

```text
smart_scheduler_demo/
├── main.py                              # 唯一入口
├── README.md
├── scheduler.py                         # 排班生成与规则校验
├── data/
│   ├── employees.json
│   └── rules.json
├── static/
│   ├── agent_v3.html                    # 三模式页面
│   ├── export_tools.js                  # Markdown/CSV 生成与下载
│   └── export_tools.css
├── deepseek_agent/
│   ├── deepseek_app.py                  # 排班与追加核心
│   ├── deepseek_app_v3.py               # 解释功能
│   ├── deepseek_app_v4.py               # 导出功能与正式服务
│   ├── deepseek_client.py
│   └── explanation_client.py
├── tests/
│   ├── test_scheduler.py
│   ├── test_append_mode.py
│   ├── test_explanation_mode.py
│   └── test_export_ui.py
├── 排班规则.md
├── 员工名单.md
└── legacy/                              # 历史版本，不参与运行
```

## 核心规则

- 每班至少 1 名店长值守、2 名饮品制作、1 名收银人员。
- 工作日每班至少 4 人，周末每班至少 6 人。
- 每人每天最多 1 班、每周最多 5 班。
- 不得连续工作超过 5 天。
- 晚班后不得接次日早班。
- 请假和不可工作日期不得排班。
- 不得虚构员工技能。

## 测试

```powershell
python -m unittest discover -s tests -v
node --check static\export_tools.js
```

当前 10 个测试覆盖排班生成、违规检测、追加需求、自动修复、只读解释和导出资源。

## AI 工具使用记录

- AI 辅助生成自然语言解析、Web Server、排班算法、修订流程、解释器、导出工具和测试。
- 员工数据来自题目图片转录，正式提交前应再次人工复核。
- DeepSeek 负责理解、修订建议和解释；最终排班由确定性 Python 校验器把关。
