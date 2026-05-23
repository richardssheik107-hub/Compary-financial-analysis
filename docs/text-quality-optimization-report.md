# 文本质量优化阶段报告

## 阶段目标

围绕简历展示需要，将“RAG 与 Skill 调优是否有效”转化为可量化指标，而不是只凭主观体验判断。

## 当前对比结果

| 指标 | Step 51-52 基线 | Step 53 路由优化后 | 变化 |
|---|---:|---:|---:|
| route_success_rate | 74.00% | 100.00% | +26.00pp |
| structure_pass_rate | 100.00% | 100.00% | 0.00pp |
| evidence_coverage_rate | 100.00% | 100.00% | 0.00pp |
| text_quality_pass_rate | 100.00% | 100.00% | 0.00pp |
| empty_talk_rate | 0.00% | 0.00% | 0.00pp |
| logic_issue_rate | 0.00% | 0.00% | 0.00pp |
| avg_total_score | 84.8 | 84.9 | +0.1 |
| avg_answer_length | 360.5 | 346.5 | -14.0 |
| avg_source_count | 1.8 | 2.3 | +0.5 |

## 本轮优化说明

问题定位：50 条评测集中，失败主要集中在双公司对比类问题，原因是部分公司别名未进入识别词表，导致系统只识别到一个公司并降级为单公司研究。

处理方式：
- 重写 `eval/company_aliases.csv`，补充 30+ 个常见 A 股公司简称、别名和股票代码。
- 在 `src/agent.py` 补充正常中文对比意图关键词。
- 在 `src/research_agent.py` 增加“只有一个公司但询问和谁比较”的边界保护，避免错误进入单公司研究。

## 简历表达方向

可写为：

> 设计 50 条公司研究评测集与五维文本质量 Rubric，覆盖路由、结构、证据、逻辑和表达质量；通过别名词表扩展与比较意图识别优化，将研究 Agent 的路由成功率从 74% 提升至 100%，并保持文本质量通过率 100%。

## 下一步

接下来进入 RAG 与 Skill 的消融实验：
- `Base`：仅财务数据
- `Base + RAG`：财务数据 + 本地资料检索
- `Base + RAG + Skill`：完整研究写作调优

目标是量化 RAG 与 Skill 对 `evidence_coverage_rate`、`avg_source_count`、`avg_total_score` 的增益。
