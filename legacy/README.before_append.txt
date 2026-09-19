# 智能排班 Agent（DSAgent）

这是场景 C“智能排班助手”的可运行 Demo。用户使用自然语言描述排班需求，DeepSeek V4.1 Flash 负责理解意图，Python 排班器生成方案，独立校验器检查 R-01～R-09。

## 快速启动

环境要求：Python 3.10 或更高版本。

在项目目录运行唯一入口：

```powershell
python main.py
```

首次启动时，程序会提示：

```text
DeepSeek API Key:
```

粘贴 DeepSeek API Key 并回车，然后访问：

<http://127.0.0.1:8000>

API Key 只保存在本机的 `deepseek_agent/deepseek_key.txt`，该文件已被 `.gitignore` 忽略。DeepSeek 的 API 地址和模型名称已固定，用户不需要填写其他配置。

## 系统架构

```text
用户自然语言
  → DeepSeek V4.1 Flash 意图理解
  → JSON Schema 结构化请求
  → Python 确定性排班器
  → R-01～R-09 独立校验
  → 排班表 / 冲突原因 / 澄清问题
```

固定配置：

- API：`https://api.deepseek.com/responses`
- 模型：`deepseek-flash`，对应 DeepSeek V4.1 Flash

DeepSeek 只负责理解自然语言，不直接修改员工技能或绕过硬性规则。

## 支持的自然语言

示例：

- “帮我生成下周完整排班，尽量照顾员工偏好。”
- “只生成周末的早晚班。”
- “工作日只排早班，不考虑偏好。”
- “帮我排一周，尽量让大家的工作量均衡。”

基础版支持理解：

- 整周、工作日、周末或指定星期
- 早班、晚班或全部班次
- 是否考虑员工班次偏好
- 是否平衡工作量

如果请求包含基础版暂不支持的临时规则，Agent 会向用户追问，而不是擅自忽略。

## 项目结构

```text
smart_scheduler_demo/
├── main.py                         # 唯一项目入口
├── README.md                       # 唯一项目说明
├── scheduler.py                    # 排班生成与独立规则校验
├── data/
│   ├── employees.json              # 员工结构化数据
│   └── rules.json                  # 排班规则结构化数据
├── static/
│   └── agent.html                  # Web 页面
├── deepseek_agent/
│   ├── deepseek_app.py             # DSAgent Web Server
│   ├── deepseek_client.py          # DeepSeek Responses API 客户端
│   └── deepseek_key.txt             # 本地密钥，首次运行后生成
├── tests/
│   └── test_scheduler.py           # 排班器测试
├── 排班规则.md
└── 员工名单.md
```

`app.py`、`agent_app.py` 和旧启动脚本属于早期原型，正式演示统一使用 `python main.py`。

## 核心规则

- 每班至少 1 名店长值守人员。
- 每班至少 2 名饮品制作人员。
- 每班至少 1 名收银人员。
- 工作日每班至少 4 人，周末每班至少 6 人。
- 每人每周最多 5 班、每天最多 1 班。
- 不得连续工作超过 5 天。
- 晚班后不得接次日早班。
- 请假和不可工作日期不得排班。
- 不得虚构员工技能。

完整规则见 `排班规则.md`，员工数据见 `员工名单.md`。

## 测试

```powershell
python -m unittest discover -s tests -v
```

Demo 前至少验证：

1. 完整一周可以生成 14 个班次。
2. 页面显示 R-01～R-09 全部通过。
3. 周末请求只生成周六和周日。
4. API Key 无效时页面明确提示降级模式。

## AI 工具使用记录

- AI 辅助生成了自然语言解析接口、Web Server、排班算法、规则校验器、页面及测试代码。
- 员工数据来自题目图片转录，正式提交前应再次人工复核。
- DeepSeek 只负责自然语言意图识别，排班结果由确定性 Python 程序生成。
- 所有生成结果均由独立校验器逐条检查 R-01～R-09。
