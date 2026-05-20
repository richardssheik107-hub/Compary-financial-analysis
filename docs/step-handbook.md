# 大白话财报 Agent：步骤合集手册（Step 1 - Step 17）

## 使用说明

这份文档用于把阶段说明文档集中在一起，便于快速查看每一步的目标、改动和验收点。  
如果要看详细设计，请打开每一步后面的“原文档”链接。

## Step 1：建立 Agent 基线

- 目标：把原有“直接调用数据层+AI层”的流程升级为统一 Agent 入口。
- 关键改动：
  - 新增 `run_financial_agent(query)`
  - 页面新增 Agent 执行过程
  - 建立阶段文档 + 当日日志双轨记录
- 验收点：
  - 可启动
  - 可分析
  - 无 API Key 不崩溃
- 原文档：[step-01-agent-baseline.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-01-agent-baseline.md)

## Step 2：ToolRegistry 与质量评估

- 目标：让 Agent 从“流程可见”升级到“工具可见+质量可评估”。
- 关键改动：
  - 新增 `ToolRegistry`
  - 新增工具调用明细
  - 新增输出质量评估卡片
- 验收点：
  - 每步显示工具名
  - 显示工具成功/失败
  - 显示质量分与判定项
- 原文档：[step-02-tool-registry-evaluation.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-02-tool-registry-evaluation.md)

## Step 3：双公司对比流程

- 目标：支持“对比/比较/谁更好”类问题。
- 关键改动：
  - 识别两个公司
  - 分别取数与解读
  - 输出对比结论与指标表
- 验收点：
  - 对比问题可出结果
  - 单公司流程不回归
  - 失败时有明确提示
- 原文档：[step-03-compare-flow.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-03-compare-flow.md)

## Step 4：可信度与行业语境

- 目标：让对比结论具备边界感与可解释性。
- 关键改动：
  - 增加 `confidence_score`
  - 增加行业语境、限制说明
  - 增加建议继续追问
- 验收点：
  - 对比结果显示可信度
  - 显示限制和后续建议
- 原文档：[step-04-compare-confidence-followups.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-04-compare-confidence-followups.md)

## Step 5：追问一键触发

- 目标：把追问从“手动输入”升级为“按钮触发”。
- 关键改动：
  - 追问按钮点击后自动回填
  - 自动触发下一轮分析
  - 修复 Streamlit 状态重跑问题
- 验收点：
  - 点击追问后自动分析
  - 输入框回填稳定
- 原文档：[step-05-clickable-followups.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-05-clickable-followups.md)

## Step 6：一键冒烟回归

- 目标：形成每次改动后的快速回归能力。
- 关键改动：
  - 新增 `scripts/smoke_check.py`
  - 覆盖健康检查/单公司/双公司/失败提示
- 验收点：
  - 脚本一次执行给出结构化结果
  - 全通过退出码 0，失败退出码 1
- 原文档：[step-06-smoke-check.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-06-smoke-check.md)

## Step 7：通用问题模式

- 目标：用户不提具体公司时也能输出可用结果。
- 关键改动：
  - 新增 `analyze_general_question`
  - 识别失败时自动切换通用模式
  - 页面显示“通用问题模式”
- 验收点：
  - 泛化问题可返回结构化解读
  - 单公司/双公司流程不回归
- 原文档：[step-07-general-question-mode.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-07-general-question-mode.md)

## Step 8：统一追问建议

- 目标：让任何场景都能继续问，不中断。
- 关键改动：
  - `AgentResult` 增加 `suggested_questions`
  - 通用/单公司/双公司统一返回追问建议
  - 前端统一渲染“你可以继续这样问”
- 验收点：
  - 三类场景都返回建议
  - 建议可点击并触发下一轮
- 原文档：[step-08-unified-followup-suggestions.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-08-unified-followup-suggestions.md)

## Step 9：会话上下文记忆

- 目标：让连续追问具备上下文继承能力。
- 关键改动：
  - 增加上下文补全字段（resolved query / context used）
  - 增加上下文状态条和清空按钮
- 验收点：
  - “它/这家公司”类问题可继承上一轮公司
- 原文档：[step-09-conversation-memory.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-09-conversation-memory.md)

## Step 10：追问场景精简回答

- 目标：追问时只展示与问题直接相关的文字内容。
- 关键改动：
  - 增加精简渲染模式（文字优先）
- 验收点：
  - 追问不再重复展示全量图表与复杂面板
- 原文档：[step-10-followup-concise-answer.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-10-followup-concise-answer.md)

## Step 11：移除追问按钮功能

- 目标：简化交互链路，去掉自动追问功能。
- 关键改动：
  - 删除追问按钮、自动回填与自动执行状态链路
- 验收点：
  - 页面无追问按钮，主流程稳定
- 原文档：[step-11-followup-feature-removal.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-11-followup-feature-removal.md)

## Step 12：上下文存储标准化

- 目标：将上下文从散落字段收敛为统一结构，便于扩展。
- 关键改动：
  - 新增 `ConversationContext`
  - app 统一读写 `conversation_context`
  - 旧键自动迁移
- 验收点：
  - 上下文逻辑不回归且状态一致性提升
- 原文档：[step-12-context-store-standardization.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-12-context-store-standardization.md)

## Step 13：提交后二次重跑稳定性修复

- 目标：修复上下文栏不实时和结果区偶发渲染异常。
- 关键改动：
  - 提交后立即 `st.rerun()`
  - 次轮统一渲染上下文与结果
- 验收点：
  - 上下文栏实时更新
  - 延申问题区域稳定显示
- 原文档：[step-13-submit-rerun-stability-fix.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-13-submit-rerun-stability-fix.md)

## Step 14：顶部上下文栏实时刷新修复

- 目标：解决提交后上下文栏显示旧状态的问题。
- 关键改动：
  - 使用顶部容器占位
  - 提交处理后再写入上下文栏渲染
- 验收点：
  - 上下文栏同轮反映最新公司/对比对
- 原文档：[step-14-context-bar-live-refresh-fix.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-14-context-bar-live-refresh-fix.md)

## Step 15：顶部上下文栏 DOM 稳定性修复

- 目标：修复前端 DOM 异常导致的上下文栏不稳定显示。
- 关键改动：
  - 上下文栏改为 Streamlit 原生组件渲染
- 验收点：
  - 页面可稳定加载，顶部上下文栏持续可见
- 原文档：[step-15-context-bar-dom-stability-fix.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-15-context-bar-dom-stability-fix.md)

## Step 16：动态结果区原生渲染兜底

- 目标：修复“无法输出内容”的前端渲染不稳定问题。
- 关键改动：
  - 动态输出区改用 Streamlit 原生组件渲染
- 验收点：
  - 页面可稳定输出结果
- 原文档：[step-16-native-render-fallback.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-16-native-render-fallback.md)

## Step 17：会话状态自愈修复

- 目标：修复旧会话缓存导致的页面不可用问题。
- 关键改动：
  - 启动时校验 `last_agent_result` 兼容性
  - 不兼容时自动清理缓存
  - 渲染异常时自动回退并提示
- 验收点：
  - 页面刷新后可恢复可用
- 原文档：[step-17-session-self-heal.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-17-session-self-heal.md)

## 建议阅读顺序

1. 先看投递总览：[job-delivery-overview.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/job-delivery-overview.md)
2. 再看这份步骤合集，快速定位到某一步
3. 最后看对应 step 文档细节和日志记录

## Step 18：可运行基线后的渐进恢复（第一轮）

- 目标：在回退稳定版本后，恢复最小可用 Agent 能力与可读执行链路。
- 关键改动：
  - `src/models.py` 补齐 Agent 结果结构
  - `src/ai_client.py` 新增 `analyze_general_question`
  - `app.py` 重建并接入 `run_financial_agent`
  - 新增上下文条、代理执行流程、延申问题建议（只读）
- 验收点：
  - 页面稳定可运行
  - 单公司 / 对比 / 通用问题均有输出
  - 顶部上下文可更新
- 原文档：[step-18-incremental-restore-baseline.md](C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/docs/step-18-incremental-restore-baseline.md)
