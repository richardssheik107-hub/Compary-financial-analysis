# Step 54：RAG + Skill 消融实验

## 目标

用统一评测集对比三种模式：

1. `Base`：关闭 RAG、关闭 Skill  
2. `Base + RAG`：开启 RAG、关闭 Skill  
3. `Base + RAG + Skill`：开启 RAG、开启 Skill

## 实现

- 新增环境开关：
  - `RESEARCH_ENABLE_RAG`（0/1）
  - `RESEARCH_ENABLE_SKILL`（0/1）
- 更新脚本：
  - `scripts/text_quality_eval_runner.py` 增加 `--mode`、`--out-csv`、`--out-md`
  - 新增 `scripts/ablation_eval_runner.py` 一键跑三组并汇总表格

## 运行命令

```powershell
python scripts/ablation_eval_runner.py --offline --limit 50
```

## 结果（N=50）

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

## 结论

目前最可见的增益在 `avg_source_count`：RAG 模式比 Base 多使用约 1 条来源，说明检索链路已生效。  
文本分数没有明显拉开，主要原因是当前离线评测集里“高质量本地资料命中样本”比例不足，Skill 也主要在语言润色层，难在现有规则中拉大差距。

## 下一步建议

为了让“RAG/Skill 提升文本质量”在指标上更明显，建议补三类样本再复测：

1. 高资料密度样本：每个公司准备 2-3 份可提取文本的报告摘要。  
2. 复杂追问样本：增加跨轮上下文问题（例如“那它的风险和上次比有没有变化”）。  
3. 难表达样本：增加“概念解释 + 对比 + 风险”复合题，观察 Skill 的结构重写增益。
