# 简历项目描述（最新版）

## 中文版（可直接贴简历）
- 设计并迭代 A 股财报分析 Agent，支持单公司分析、双公司对比、通用财务问答三类路由，构建“识别-取数-解读-追问”的完整链路。  
- 完成双公司对比产品化：输出双 K 线、财务指标对比表与文字结论，提升复杂问题可解释性与可读性。  
- 优化通用问答体验：通用问题改为“仅显示答案”，并接入智谱 `glm-4-flash` 生成高质量文本，失败场景自动兜底。  
- 建立评测与观测机制：基于 20 条测试集与自动评测脚本跟踪效果，当前达到 intent 85%、route 95%、text quality 95%。  
- 推动可运维化迭代：将公司别名从代码常量迁移到 `company_aliases.csv`，并新增 `alias_check` / `alias_suggest` 工具支持快速修复识别问题。

## 英文版（可用于英文简历）
- Built and iterated an A-share financial analysis agent with three routes: single-company analysis, two-company comparison, and general finance Q&A, forming an end-to-end pipeline from intent detection to explanation.  
- Productized the comparison workflow with dual K-line charts, side-by-side financial metrics, and narrative conclusions to improve explainability for complex user questions.  
- Improved general Q&A UX by showing answer-only output and integrating `glm-4-flash` for higher-quality responses, with robust fallback handling.  
- Established an evaluation loop using a 20-case test set and automated runner; current metrics: 85% intent accuracy, 95% route success, 95% text quality pass rate.  
- Migrated company alias management from hardcoded rules to `company_aliases.csv`, and added alias operation tooling (`alias_check`, `alias_suggest`) for faster issue recovery.
