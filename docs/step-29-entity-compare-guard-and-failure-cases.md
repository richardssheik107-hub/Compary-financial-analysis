# Step 29：实体识别增强 + 对比判定保护 + 失败样本沉淀

## 目标

围绕“公司相关问题更稳定可答”做三件事：
1. 增强公司实体识别（别名、简称、代码）；
2. 对比场景增加保护（先识别到两个实体再走对比）；
3. 评测后自动沉淀失败样本，便于下一轮定向修复。

## 本步改动

1. `src/agent.py`
- 新增 `ALIAS_TO_CANONICAL` 词表，覆盖常见简称与股票代码；
- 新增 `_extract_company_mentions(query)`，统一抽取实体；
- 调整 `_detect_intent`：
  - `财报对比` 必须满足“对比关键词 + 至少两个实体”或“双代码”；
  - 单实体+财务关键词场景优先归类为 `财报解读`；
- 调整 `_looks_like_compare_query` 与 `_extract_compare_targets`，降低误判。

2. `scripts/eval_runner.py`
- 增加工程根路径自动注入，避免 `ModuleNotFoundError: src`；
- 评测后新增 `eval/failed_cases.csv` 输出，记录：
  - `id, bucket, query, expected_intent, predicted_intent, fail_reason`

## 验证

执行：
- `python -m compileall src/agent.py scripts/eval_runner.py`
- `python scripts/eval_runner.py`

结果：
- 成功生成：`eval/failed_cases.csv`
- 评测可以自动给出失败样本列表，支持下一步定向优化。

## 当前观察

- 通用问答与单公司路由稳定性较好；
- 对比意图在部分边界样本仍有误差，后续将继续优化分词与别名词表覆盖。

## 下一步（Step 30）

1. 扩展别名词表到可配置文件（非硬编码）；
2. 对比判定引入“二次验证”（若只识别一个实体则回退单公司）；
3. 针对 `failed_cases.csv` 自动回归，逐条消减误判。
