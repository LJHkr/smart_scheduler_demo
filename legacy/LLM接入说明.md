# LLM 接入说明

## 调用链

```text
自然语言
  → LLM 结构化意图识别（严格 JSON Schema）
  → Python 确定性排班器
  → R-01～R-09 独立校验
  → 排班表或冲突说明
```

LLM 只负责理解请求，不直接修改员工技能，也不能绕过排班规则。

## 配置

1. 将 `.env.example` 复制为 `.env`。
2. 在 `.env` 中填写 API Key：

```dotenv
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-5-mini
LLM_TIMEOUT_SECONDS=30
```

`.env` 已加入 `.gitignore`，不得将真实密钥写入代码、文档或提交记录。

## 启动

双击 `启动LLM-Agent.bat`，或运行：

```bash
python agent_app.py
```

然后访问 <http://127.0.0.1:8000>。

## 降级策略

当 API Key 缺失、接口超时或 API 返回错误时，Agent 会自动使用本地关键词解析，并在页面中明确标记“本地降级解析”，保证 Demo 仍可继续。
