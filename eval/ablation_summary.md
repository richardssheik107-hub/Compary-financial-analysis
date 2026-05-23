# 消融实验结果（offline，N=50）

| 指标 | Base | Base + RAG | Base + RAG + Skill |
|---|---:|---:|---:|
| route_success_rate | 100.00% | 100.00% | 100.00% |
| structure_pass_rate | 100.00% | 100.00% | 100.00% |
| evidence_coverage_rate | 100.00% | 100.00% | 100.00% |
| text_quality_pass_rate | 100.00% | 100.00% | 100.00% |
| empty_talk_rate | 0.00% | 0.00% | 0.00% |
| logic_issue_rate | 0.00% | 0.00% | 0.00% |
| avg_total_score | 84.9 | 84.9 | 84.9 |
| avg_answer_length | 333.3 | 333.3 | 334.8 |
| avg_source_count | 1.3 | 2.3 | 2.3 |

## 文件产物

- `eval/text_quality_base.csv`
- `eval/text_quality_base_rag.csv`
- `eval/text_quality_full.csv`
