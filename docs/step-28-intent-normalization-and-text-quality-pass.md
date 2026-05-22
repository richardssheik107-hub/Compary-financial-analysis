# Step 28：意图归一化与文本质量二轮优化

## 目标

在不改动现有 UI 的前提下，提升 Agent 的可用性与稳定输出质量，重点解决：
1. 同一问题在不同分支下 `intent` 不一致；
2. 通用问答文本长度与可读性不足；
3. 局部编码污染导致维护困难。

## 本步改动

1. 重构 `src/agent.py`
- 保持 `run_financial_agent` 输入输出结构不变；
- 增加“结果意图归一化”：
  - 成功进入双公司流程时统一返回 `财报对比`；
  - 成功识别公司并产出单公司分析时统一返回 `财报解读`；
  - 未识别公司时返回 `通用财报问答`；
- 收窄对比判定，避免把普通“和/与”语句误判为对比。

2. 重构 `src/ai_client.py`
- 保持 `analyze_company` / `analyze_general_question` 对外签名不变；
- 强化通用问答文案质量：
  - 明确“收入-利润-现金流”的联动解释；
  - 提升文本完整度与可读性；
  - 保留风险提示与交易建议过滤。

3. 稳定性与兼容性
- 未改 `app.py`，避免 UI 回归；
- 保留原有 `AgentResult` / `comparison` / `suggested_questions` 字段结构。

## 回归结果

执行命令：
- `python -m compileall src/agent.py src/ai_client.py app.py`
- `$env:PYTHONPATH='.'; python scripts/eval_runner.py`

评测结果（本步）：
- total_cases: 20
- intent_accuracy: 85.00%
- route_success_rate: 95.00%
- compare_success_rate: 83.33%
- text_quality_pass_rate: 95.00%
- empty_or_error_rate: 5.00%

相较 Step 25 基线（70/85/100/60/15）：
- `text_quality_pass_rate` 明显提升；
- `empty_or_error_rate` 明显下降；
- `intent_accuracy` 提升，但仍有小样本误判待继续优化。

## 已知问题

- 对比判定仍有边界样本（如“平安银行和招商银行哪个更稳”）需要进一步规则微调；
- 个别公司名未命中常见词表时，可能落到通用问答。

## 下一步

Step 29 建议：
1. 完成“公司名词表 + 模糊别名”增强；
2. 对比意图增加“两个公司实体同时命中”的二次确认；
3. 引入 `eval` 失败样本自动沉淀机制，持续修规则。
