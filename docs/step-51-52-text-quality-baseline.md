# Step 51-52：文本质量基线与评测 Rubric

## 目标

把“文本质量好不好”从主观感受变成可重复评测的指标，为后续 RAG 与 Skill 调优提供量化对照。

## 本步产出

- `eval/research_testset.csv`：修复为 50 条正常中文评测集。
- `eval/text_quality_rubric.md`：五维文本质量评分规则。
- `scripts/text_quality_eval_runner.py`：文本质量评测脚本。
- `eval/text_quality_baseline.csv`：逐 case 评测明细。
- `eval/text_quality_baseline_summary.md`：汇总指标表格。

## 评分维度

| 维度 | 分值 | 说明 |
|---|---:|---|
| 问题相关性 | 20 | 是否直接回答用户问题 |
| 结构完整性 | 20 | 是否覆盖结论、业务、财务、风险、跟踪点 |
| 证据覆盖 | 20 | 是否有来源记录与证据绑定 |
| 逻辑一致性 | 20 | 是否避免矛盾与无依据确定性表达 |
| 表达质量 | 20 | 是否通顺、少套话、无交易建议 |

## 基线结果（offline 50 cases）

| 指标 | 结果 |
|---|---:|
| 样本数 | 50 |
| route_success_rate | 74.00% |
| structure_pass_rate | 100.00% |
| evidence_coverage_rate | 100.00% |
| text_quality_pass_rate | 100.00% |
| empty_talk_rate | 0.00% |
| logic_issue_rate | 0.00% |
| avg_total_score | 84.8 |
| avg_answer_length | 360.5 |
| avg_source_count | 1.8 |

## 初步结论

当前版本在“结构完整”和“证据标记”上表现较稳，但 `route_success_rate` 只有 74%。主要问题集中在双公司对比类问题：部分公司别名未被识别，导致预期的 `compare_companies_deep` 被降级为 `single_company_research`。

这给后续优化提供了清晰方向：
- 先扩展公司别名与对比意图识别，提高路由成功率。
- 再优化 RAG 资料命中与证据质量，提高真实资料使用率。
- 最后做 Skill 消融实验，对比 `Base / Base + RAG / Base + RAG + Skill` 的文本质量提升。

## 运行方式

快速抽样：

```powershell
python scripts/text_quality_eval_runner.py --offline --limit 10 --label baseline-offline-10
```

完整基线：

```powershell
python scripts/text_quality_eval_runner.py --offline --limit 50 --label baseline-offline-50
```
