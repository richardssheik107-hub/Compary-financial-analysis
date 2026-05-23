# Step 45-50 交付说明

## Step 45：资料治理与命名规范
- 更新 [data/reports/README.md](/C:/Users/Fergeson/Desktop/company-financial-analysis-dabaihua-v1/data/reports/README.md)。
- 明确命名模板、最小内容、命中机制与 PDF 边界说明。

## Step 46：上下文问答增强
- `run_company_research_agent` 接入会话上下文参数：
  - `context_company_name`
  - `context_stock_code`
- 前端在生成深度研究报告时传入上下文，追问问题可继承上一轮公司。

## Step 47：证据绑定输出
- `ResearchResult` 新增 `evidence_by_section`。
- 报告增加“证据绑定”展示与导出。

## Step 48：文本质量闸门
- 重构 `src/research_skill.py`，新增本地质量闸门：
  - 去敏感交易词
  - 去重复标点
  - 句尾规范化
- 无 API 时也会执行质检，保证兜底文本质量。

## Step 49：评测体系扩展
- `eval/research_testset.csv` 扩展到 50 条：
  - 单公司 20
  - 双公司 15
  - 通用问题 10
  - 边界 5

## Step 50：投递/面试交付补齐
- 本步把工程升级文档收敛到本文件，可作为“近期迭代总览”入口。
- 后续可继续补一份“演示脚本 + 10 分钟讲稿”版本。
