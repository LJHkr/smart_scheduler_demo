# 智能排班 Agent（DSAgent）

用户用自然语言描述需求，DeepSeek V4.1 Flash 负责理解和解释，Python 负责生成、修订并校验排班。所有结果必须通过 R-01～R-09。

## 启动

需要 Python 3.10 或更高版本。在项目目录运行唯一入口：

```powershell
python main.py
```

首次启动时粘贴 DeepSeek API Key，然后访问 <http://127.0.0.1:8000>。

Key 只保存在本机 `deepseek_agent/deepseek_key.txt`，并被 `.gitignore` 忽略。API 地址和模型已固定：

- API：`https://api.deepseek.com/responses`
- 模型：`deepseek-flash`，对应 DeepSeek V4.1 Flash

## 三种 Agent 模式

### 1. 从 0 排表

根据当前输入生成全新排班，并自动输出“为什么这样安排”。

示例：

- “生成下周完整排班，尽量照顾员工偏好。”
- “只生成周末的早晚班。”
- “工作日只排早班，不考虑偏好。”

### 2. 追加需求

将新要求应用到当前排班，优先做最少量修改，而不是重新随机生成整张表。

示例：

- “周三尽量不要安排 E07，其他班次不变。”
- “把 E06 的周一早班换给其他合规员工。”
- “减少 E02 的晚班，但不能违反硬规则。”

处理流程：

1. DeepSeek 读取当前排班、员工数据和追加需求。
2. 返回完整修订表，而不是局部片段。
3. Python 重新检查 R-01～R-09。
4. 首次违规时将错误反馈给 DeepSeek，并自动重试一次。
5. 只有校验通过才替换当前表，否则保留原表。
6. 页面展示相对上一版增加和移除了哪些员工，并解释修改原因。

### 3. 解释 / 提问

只读取当前排班并回答问题，绝不修改排班表。

示例：

- “为什么周三早班安排这些人？”
- “E02 为什么有这么多晚班？”
- “这张表怎样满足 R-07？”
- “哪些员工的偏好没有满足，为什么？”

解释内容包括：

- 硬规则和关键岗位覆盖依据
- 具体日期、班次及员工 ID 证据
- 员工偏好与工作量之间的取舍
- 当前结论的局限和信息边界

如果用户在解释模式要求改表，Agent 会提示切换到“追加需求”，当前表保持不变。

## 架构

```text
用户自然语言
  ├─ 从 0 排表 → DeepSeek 意图解析 → Python 排班器
  ├─ 追加需求   → 当前排班 + DeepSeek 最小修订
  └─ 解释/提问  → 当前排班 + DeepSeek 只读解释
                                  ↓
                         R-01～R-09 独立校验
```

DeepSeek 不得自行添加员工技能或绕过规则。解释器与修改接口分离，解释请求没有写入排班的路径。

## 项目结构

```text
smart_scheduler_demo/
├── main.py                              # 唯一入口，启动可解释 DSAgent
├── README.md
├── scheduler.py                         # 排班生成与规则校验
├── data/
│   ├── employees.json
│   └── rules.json
├── static/
│   └── agent_v3.html                    # 三模式 Web 页面
├── deepseek_agent/
│   ├── deepseek_app.py                  # 排班与追加核心
│   ├── deepseek_app_v3.py               # 三模式 API 服务
│   ├── deepseek_client.py               # 意图解析与排班修订
│   ├── explanation_client.py            # 只读解释器
│   └── deepseek_key.txt                  # 本机密钥
├── tests/
│   ├── test_scheduler.py
│   ├── test_append_mode.py
│   └── test_explanation_mode.py
├── 排班规则.md
├── 员工名单.md
└── legacy/                              # 可恢复的历史版本，不参与运行
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
```

现有 9 个测试覆盖：排班生成、规则违规检测、追加需求、自动修复重试、自动解释、无基础表拒绝解释，以及解释问答不修改排班。

## AI 工具使用记录

- AI 辅助生成自然语言解析、Web Server、排班算法、修订流程、解释器、校验器、页面和测试。
- 员工数据来自题目图片转录，正式提交前应再次人工复核。
- DeepSeek 负责理解、修订建议和解释，最终排班由确定性 Python 校验器把关。
