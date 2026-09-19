# 智能排班 Agent（DSAgent）

用户用自然语言描述排班需求，DeepSeek V4.1 Flash 负责理解意图，Python 排班器生成或修订方案，独立校验器检查 R-01～R-09。

## 快速启动

需要 Python 3.10 或更高版本。在项目目录运行唯一入口：

```powershell
python main.py
```

首次启动时粘贴 DeepSeek API Key，然后访问：

<http://127.0.0.1:8000>

Key 只保存在本机 `deepseek_agent/deepseek_key.txt`，该文件已被 `.gitignore` 忽略。API 地址和模型名称已经固定，无需填写其他配置。

## 两种排班模式

页面顶部提供切换按钮：

### 从 0 开始排表

根据当前输入创建全新排班，并将它设为页面中的当前排班表。

示例：

- “帮我生成下周完整排班，尽量照顾员工偏好。”
- “只生成周末的早晚班。”
- “工作日只排早班，不考虑偏好。”

### 追加需求

把新要求应用到当前已有排班，优先进行最少量修改，而不是重新随机生成整张表。

示例：

- “周三尽量不要安排 E07，其他班次不变。”
- “把 E06 的周一早班换给其他合规员工。”
- “尽量减少 E02 的晚班，但不能违反硬规则。”

追加流程：

1. 页面把当前排班、员工数据和新要求发送给 DeepSeek。
2. DeepSeek 返回完整修订表和需求满足依据。
3. Python 校验器重新检查 R-01～R-09。
4. 校验失败时，将错误反馈给 DeepSeek并自动重试一次。
5. 只有通过校验才替换当前表，否则保留原表。
6. 页面展示相对上一版增加和移除了哪些员工。

修改后的版本可以继续接收下一条追加需求。

## 系统架构

```text
用户自然语言
  ├─ 从 0 开始 → DeepSeek 意图解析 → Python 排班器
  └─ 追加需求   → 当前排班 + DeepSeek 最小修订
                                ↓
                        R-01～R-09 独立校验
                                ↓
                     新排班 / 冲突原因 / 追问
```

固定配置：

- API：`https://api.deepseek.com/responses`
- 模型：`deepseek-flash`，对应 DeepSeek V4.1 Flash

DeepSeek 负责自然语言理解和修订建议，不得自行添加员工技能或绕过硬性规则。

## 当前支持的需求

- 整周、工作日、周末或指定星期
- 早班、晚班或全部班次
- 是否考虑员工班次偏好
- 是否平衡工作量
- 在已有表上指定员工、日期或班次的调整需求

需求含糊或与硬规则冲突时，Agent 会追问或保留原表，不会静默忽略。

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
│   └── agent.html                  # 双模式 Web 页面
├── deepseek_agent/
│   ├── deepseek_app.py             # DSAgent Web Server
│   ├── deepseek_client.py          # DeepSeek API 与排班修订
│   └── deepseek_key.txt             # 本地密钥，首次运行生成
├── tests/
│   ├── test_scheduler.py
│   └── test_append_mode.py
├── 排班规则.md
├── 员工名单.md
└── legacy/                         # 可恢复的早期实现，不参与运行
```

## 核心规则

- 每班至少 1 名店长值守、2 名饮品制作、1 名收银人员。
- 工作日每班至少 4 人，周末每班至少 6 人。
- 每人每天最多 1 班、每周最多 5 班。
- 不得连续工作超过 5 天。
- 晚班后不得接次日早班。
- 请假和不可工作日期不得排班。
- 不得虚构员工技能。

完整规则见 `排班规则.md`，员工数据见 `员工名单.md`。

## 测试

```powershell
python -m unittest discover -s tests -v
```

当前测试覆盖：完整周排班、周末解析、违规检测、无基础表拒绝追加、有效追加，以及违规修订后的自动重试。

## AI 工具使用记录

- AI 辅助生成自然语言解析、Web Server、排班算法、修订流程、规则校验、页面和测试。
- 员工数据来自题目图片转录，正式提交前应再次人工复核。
- DeepSeek 只负责理解和修订建议，最终结果必须通过确定性 Python 校验器。
