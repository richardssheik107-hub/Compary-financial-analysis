# 大白话财报

消费级智能投顾 AI 助手 MVP。用户用自然语言提问，应用优先抓取 A 股财务数据，并调用大模型把财报指标翻译成更容易理解的中文说明。

## Windows 启动

1. 复制 `.env.example` 为 `.env`，填写 `OPENAI_API_KEY`。
2. 双击 `start.bat`。
3. 浏览器打开 `http://localhost:8501`。

没有配置 API Key 时，应用不会崩溃，会展示本地演示解读并提示如何开启真实 AI 分析。

首次启动会自动创建 `.venv` 虚拟环境并安装依赖，时间可能较长。若安装失败，优先检查 Python 3、网络连接和 pip 是否可用。

## 环境变量

- `OPENAI_API_KEY`：必填，真实 AI 分析所需。
- `OPENAI_BASE_URL`：可选，OpenAI 兼容接口地址。
- `OPENAI_MODEL`：可选，默认 `gpt-4o-mini`。

## 国内模型配置示例

项目使用 OpenAI 兼容接口。复制 `.env.example` 为 `.env` 后，只保留一个模型供应商配置。

智谱 AI / BigModel：

```env
OPENAI_API_KEY=your_new_api_key_here
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

阿里云百炼 / 通义千问：

```env
OPENAI_API_KEY=your_new_api_key_here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

Kimi / Moonshot：

```env
OPENAI_API_KEY=your_new_api_key_here
OPENAI_BASE_URL=https://api.moonshot.ai/v1
OPENAI_MODEL=moonshot-v1-8k
```

不要把真实 API Key 提交到项目里。如果 Key 曾经暴露在聊天、截图或日志中，建议立即在平台后台作废并重新生成。

## MVP 范围

- 第一版只支持 A 股优先。
- 使用 AKShare 获取公开数据，接口失败时使用内置样例兜底。
- 内容仅用于财报理解和投资教育，不构成投资建议。
