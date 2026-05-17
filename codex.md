# Codex 工作指引

## 项目目标

本项目是“大白话财报”，一个 Windows 本地运行的消费级智能投顾 AI 助手 MVP。核心目标是帮助普通用户用自然语言理解 A 股公司财报，不提供直接交易建议。

## 标准文件路径

- 产品需求：`docs/requirements.md`
- 技术设计：`docs/technical_design.md`
- 设计规范：`docs/design_guidelines.md`
- 分步执行计划：`docs/execution_steps.md`
- MVP 验收清单：`docs/acceptance_checklist.md`
- 每日开发日志流程：`docs/daily_workflow.md`
- 开发日志目录：`dev_logs/`
- 日志生成脚本：`scripts/dev_log.py`
- 应用入口：`app.py`
- 数据层：`src/data_service.py`
- AI 层：`src/ai_client.py`
- 样例数据：`src/sample_data.py`
- Windows 启动脚本：`start.bat`
- 依赖清单：`requirements.txt`

## 工作方式

- 每次只推进一个小目标，不要同时大改数据层、AI 层和 UI。
- 开始开发前先阅读相关 `docs/` 文件。
- 修改代码前先确认当前目标属于 `docs/execution_steps.md` 的哪个步骤。
- 完成任务后更新当天 `dev_logs/YYYY-MM-DD.md`。
- 若有新增约定或设计变化，先更新 `docs/` 中对应文件。

## 开发日志要求

- 每天至少维护一个日志文件，命名格式为 `YYYY-MM-DD.md`。
- 已配置每日 18:00 Codex 自动提醒，检查并协助补齐当天日志。
- 每次开发结束必须记录：
  - 今日完成
  - 当前待办
  - 风险与阻塞
  - 下一步建议
- 可用以下命令生成或补齐日志：

```powershell
python scripts/dev_log.py
```

也可以追加条目：

```powershell
python scripts/dev_log.py --done "完成某项开发" --todo "下一步事项"
```

## 质量标准

- 应用必须能在缺少 API Key 时优雅降级。
- AKShare 调用失败时必须启用样例兜底。
- 大模型输出必须保持 JSON 结构稳定。
- 页面必须显示风险提示。
- 输出不得包含直接交易建议，例如“买入”“卖出”“重仓”“梭哈”。

## 验证顺序

1. `python -m compileall app.py src scripts`
2. `python scripts/dev_log.py`
3. 缺少 API Key 场景下运行 Streamlit。
4. 配置真实 API Key 后运行完整查询。

## 安全边界

- 不提交 `.env` 或任何 API Key。
- 不删除用户已有文件。
- 不把虚拟环境、缓存文件或临时输出当作项目交付物。
