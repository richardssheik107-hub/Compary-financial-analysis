# 技术设计

## 技术栈

- Python
- Streamlit
- AKShare
- OpenAI Python SDK 或兼容 OpenAI 协议的大模型服务
- Plotly
- python-dotenv

## 代码结构

- `app.py`：Streamlit 页面入口，负责交互、布局和图表展示。
- `src/data_service.py`：公司识别、AKShare 数据获取、样例数据兜底。
- `src/ai_client.py`：大模型调用、JSON 解析、合规词替换、本地兜底分析。
- `src/models.py`：分析结果的数据结构。
- `src/sample_data.py`：演示企业样例数据。

## 数据流

1. 用户输入自然语言问题。
2. 系统根据别名表识别公司名称和股票代码。
3. 系统尝试通过 AKShare 获取财务指标。
4. 若 AKShare 失败或结果不足，使用内置样例数据补齐。
5. 系统将结构化数据和用户问题发送给大模型。
6. 大模型返回固定 JSON 结构。
7. 前端将 0-10 分转换为 0-100 分并渲染雷达图。

## 可靠性策略

- OpenAI SDK 懒加载，缺依赖时进入本地兜底。
- 缺少 `OPENAI_API_KEY` 时进入本地兜底。
- 大模型返回非标准 JSON 时尝试提取 JSON 片段。
- 分数强制限制在 0-10。
- 输出文本做直接交易词替换。
- AKShare 财务摘要按最新报告期列取值，金额统一格式化为“亿元”，并保留内置样例作为缺字段兜底。
- 股票代码识别使用 6 位数字提取规则，支持代码独立输入或夹在自然语言中输入。
- AI 输出必须包含固定 JSON 字段，缺字段、分数越界或接口异常时进入本地兜底。
- 本地兜底会根据收入同比、利润同比、现金流与利润关系生成基础评分，而不是固定分数。

## 配置

- `OPENAI_API_KEY`：真实 AI 分析必需。
- `OPENAI_BASE_URL`：可选，兼容第三方模型服务。
- `OPENAI_MODEL`：可选，默认模型在代码中设置。

## OpenAI 兼容模型供应商

可通过 `.env` 切换模型供应商，不需要改代码。

- 智谱 AI / BigModel：`OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4`，示例模型 `glm-4-flash`。
- 阿里云百炼 / 通义千问：`OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`，示例模型 `qwen-plus`。
- Kimi / Moonshot：`OPENAI_BASE_URL=https://api.moonshot.ai/v1`，示例模型 `moonshot-v1-8k`。

真实 API Key 只允许写入本地 `.env`，不得写入 README、日志、截图或提交记录。
