# Step 25：评测基线落地（Day 1）

## 目标

搭建可量化评测基线，支撑后续文本与路由优化迭代。

## 本步交付

1. 指标文档  
- 文件：`eval/metrics.md`  
- 内容：意图准确率、路由成功率、对比成功率、文本质量通过率、空结果率。

2. 测试集  
- 文件：`eval/testset.csv`  
- 规模：20 条（single_company / compare / general 三类）。

3. 评测脚本  
- 文件：`scripts/eval_runner.py`  
- 能力：读取测试集、调用 `run_financial_agent`、输出总体与分桶指标、失败样例。

## 基线结果（首次运行）

- total_cases: 20
- intent_accuracy: 70.00%
- route_success_rate: 85.00%
- compare_success_rate: 100.00%
- text_quality_pass_rate: 60.00%
- empty_or_error_rate: 15.00%

分桶结果：
- compare: intent 83.33%, route 100.00%, text 100.00%
- general: intent 83.33%, route 83.33%, text 0.00%
- single_company: intent 50.00%, route 75.00%, text 75.00%

## 结论

1. 对比链路已经稳定（可作为当前项目亮点）。  
2. 单公司意图识别与通用问答文本质量仍是主要短板。  
3. 后续优化优先级：  
- 单公司意图识别（公司名/代码直达识别）  
- 通用问答文本质量规则（提升 general 桶的 text pass）
