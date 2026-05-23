# 文本质量评测 Rubric（Step 52）

总分 100 分，分为 5 个维度，每个维度 20 分。

| 维度 | 分值 | 判断标准 |
|---|---:|---|
| 问题相关性 | 20 | 是否直接回答用户问题，是否命中问题中的公司、指标或比较意图 |
| 结构完整性 | 20 | 是否包含结论、业务、经营表现、盈利质量、现金流、成长/行业、风险、跟踪清单 |
| 证据覆盖 | 20 | 是否包含来源记录、证据绑定、财务数据/资料/模型推断标识 |
| 逻辑一致性 | 20 | 是否避免前后矛盾、证据和结论不匹配、无依据确定性表达 |
| 表达质量 | 20 | 是否通顺、少套话、无交易建议、长度足够、标点规范 |

## 核心指标

| 指标 | 含义 |
|---|---|
| `route_success_rate` | 路由是否进入预期类型 |
| `structure_pass_rate` | 结构得分是否达到 18/20 |
| `evidence_coverage_rate` | 是否有来源或证据绑定 |
| `text_quality_pass_rate` | 总分是否达到 80/100 |
| `empty_talk_rate` | 是否存在空泛套话 |
| `logic_issue_rate` | 是否存在明显逻辑冲突 |
| `avg_total_score` | 平均文本质量总分 |
| `avg_answer_length` | 平均回答长度 |
| `avg_source_count` | 平均来源记录数 |

## 使用方式

```powershell
python scripts/text_quality_eval_runner.py --offline --limit 10 --label baseline-offline-10
```

完整评测：

```powershell
python scripts/text_quality_eval_runner.py --offline --limit 50 --label baseline-offline-50
```
