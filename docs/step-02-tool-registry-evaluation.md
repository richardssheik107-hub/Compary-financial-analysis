# Step 2 说明文档：ToolRegistry 与输出质量评估

## 1. 目标

在 Step 1 最小 Agent 基线上，补齐两项能力：

- 工具级编排可见化：明确每次调用了什么工具、是否成功、返回了什么摘要
- 输出质量可量化：对风险提示、数据来源、交易词合规、核心指标解释进行评分

## 2. 本步改动

- 在 `src/agent.py` 新增轻量 `ToolRegistry`，统一调度：
  - `build_company_snapshot`
  - `analyze_company`
- 在 `src/models.py` 扩展 Agent 结构：
  - `ToolCallResult`
  - `EvaluationResult`
  - `AgentStep.tool_name`
  - `AgentResult.tool_calls` / `AgentResult.evaluation`
- 在 `app.py` 增加展示区：
  - 工具调用明细
  - 输出质量评估卡片（0-100）

## 3. 设计决策

- 仍采用轻量本地实现，不引入重型框架，保证学习和求职演示友好。
- 质量评估用规则法，优先保证可解释、可复现、可调参。
- 评分不替代业务判断，只用于质量门禁和演示复盘。

## 4. 验收标准

- 查询成功时，页面可见：
  - Agent 执行步骤（含 tool name）
  - 工具调用明细（含成功/失败）
  - 输出质量评估分数和判定项
- 查询失败时，失败步骤和错误信息可见。
- 原有白话解读、图表、风险提示不回归。

## 5. 测试指引

- 输入 `贵州茅台`：
  - 预期 `build_company_snapshot` 与 `analyze_company` 显示成功
  - 质量评估卡片显示分数
- 输入 `帮我看看000001`：
  - 预期识别平安银行且步骤完整
- 输入无效文本：
  - 预期出现失败步骤和提示，不崩溃

## 6. 下一步

- Step 3 可继续做：
  - 工具入参与出参片段展示
  - 质量评估规则外置配置
  - 对比场景（双公司）专用 Agent 流程
