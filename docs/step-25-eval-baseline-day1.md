# Step 25：评测体系与版本对比（更新版）

## 目标
建立可量化评测体系，用数据驱动 Agent 迭代，而不是靠主观感觉判断“变好没有”。

## 评测资产
1. 测试集：`eval/testset.csv`（20 条，覆盖 single/compare/general）  
2. 评测脚本：`scripts/eval_runner.py`  
3. 失败样本：`eval/failed_cases.csv`（每次评测自动更新）

## 指标定义
- `intent_accuracy`：意图识别准确率  
- `route_success_rate`：路由成功率  
- `compare_success_rate`：对比分支成功率  
- `text_quality_pass_rate`：文本质量通过率  
- `empty_or_error_rate`：空结果或错误率

## 基线与当前对比
### Day1 基线
- intent_accuracy: 70.00%
- route_success_rate: 85.00%
- compare_success_rate: 100.00%
- text_quality_pass_rate: 60.00%
- empty_or_error_rate: 15.00%

### 当前版本（Step 30+）
- intent_accuracy: 85.00%
- route_success_rate: 95.00%
- compare_success_rate: 83.33%
- text_quality_pass_rate: 95.00%
- empty_or_error_rate: 5.00%

## 解读
1. 文本质量和可用性已明显提升（text quality、route、error）。  
2. compare 成功率仍有边界样本，需要继续优化别名与意图规则。  
3. 失败样本机制已就位，可持续收敛问题。

## 后续动作
1. 结合 `failed_cases.csv` 增量补词表与规则。  
2. 继续扩展 compare 场景样本，防止“修一处坏一处”。  
3. 增加多轮上下文测试集，覆盖追问链路。
