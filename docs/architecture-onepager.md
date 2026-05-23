# 架构一页纸（最新版）

## 1. 目标
构建一个可解释、可追踪、可持续迭代的财报分析 Agent，覆盖：
- 单公司分析
- 双公司对比
- 通用财务问答

## 2. 主流程
用户输入  
-> `run_financial_agent`（意图识别与路由）  
-> 数据工具（公司识别、AKShare 抓取、兜底）  
-> 模型解读（`glm-4-flash`/兜底）  
-> Streamlit 渲染（单公司、对比、通用答案）  
-> 会话上下文更新

## 3. 核心模块
1. `src/agent.py`  
- 意图识别：财报解读 / 财报对比 / 通用问答  
- 对比分支二次验证：识别不足时自动回退单公司  
- 输出结构化 `AgentResult`

2. `src/data_service.py`  
- 公司识别与 snapshot 构建  
- 财务指标、日线数据抓取  
- 数据失败兜底

3. `src/ai_client.py`  
- 单公司与通用问答的模型解读  
- 合规限制（风险提示、禁止交易指令）  
- API 异常 fallback

4. `app.py`  
- 单公司页面：评分、雷达、K 线、财务表、文本  
- 对比页面：双 K 线、对比表、对比结论  
- 通用问题页面：仅显示答案文本

5. `src/company_aliases.py` + `eval/company_aliases.csv`  
- 别名数据化配置  
- 支持缓存与刷新  
- 降低识别迭代成本

6. `scripts/*`  
- `eval_runner.py`：自动评测  
- `alias_check.py`：别名生效检查  
- `alias_suggest.py`：失败样本别名建议

## 4. 质量与稳定性
- 评测数据：`eval/testset.csv`（20 条）  
- 最新指标：intent 85%、route 95%、text quality 95%  
- 健康检查：`/_stcore/health = ok`

## 5. 当前风险与后续
- compare 边界样本仍需继续收敛。  
- 通用问答需继续做事实约束和风格稳定。  
- 下一阶段可做一键流水线：新增别名 -> 检查 -> 评测 -> 报告。
