# DeepSeek V4.1 Flash 排班 Agent

用户只需要提供一个 DeepSeek API Key。接口地址和模型名称已经固定：

- API：`https://api.deepseek.com/responses`
- 模型：`deepseek-flash`，对应 DeepSeek V4.1 Flash

## 最简单的启动方式

双击 `启动DeepSeek-Agent.bat`。

首次运行时，在窗口中粘贴 DeepSeek API Key 并按回车。程序会把密钥保存在当前目录的 `deepseek_key.txt` 中，然后启动服务。

浏览器访问：<http://127.0.0.1:8000>

## 手动配置

也可以复制 `deepseek_key.txt.example`，将副本改名为 `deepseek_key.txt`，删除说明文字并只保留一行 API Key。

`deepseek_key.txt` 已加入 `.gitignore`，不得发送给他人或提交到 Git。

## Agent 行为

1. DeepSeek V4.1 Flash 将自然语言解析为严格的结构化排班意图。
2. Python 排班器根据员工数据生成方案。
3. 独立校验器检查 R-01～R-09。
4. DeepSeek API 不可用时自动进入本地降级模式，并在页面明确提示。
