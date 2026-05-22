# Step 30：词表外置与对比二次验证

## 目标

继续提升“公司相关问题”的鲁棒性，重点完成：
1. 公司别名词表外置，降低硬编码维护成本；
2. 对比模式二次验证：仅识别到一个公司时不报错，自动回退单公司；
3. 保持 UI 与主流程不回归。

## 本步改动

1. 新增词表配置文件
- 文件：`src/company_aliases.py`
- 内容：`ALIAS_TO_CANONICAL`，集中维护“公司简称/别名/代码 -> 标准名称”的映射。
- 价值：后续扩展词表时无需改 `agent.py` 主逻辑。

2. 重构 `src/agent.py`
- 使用 `src/company_aliases.py` 提供的词表；
- 将实体提取、意图识别与对比判断流程结构化：
  - `_extract_company_mentions`
  - `_has_compare_keyword`
  - `_looks_like_compare_query`
- 新增“对比二次验证回退”：
  - 对比分支若只识别到一个公司，则自动回退到单公司分析；
  - 返回警告说明“已自动回退单公司解读”。

3. 保持兼容
- 保持 `run_financial_agent` 入参和 `AgentResult` 出参结构不变；
- 未改 UI 文件（`app.py`）。

## 回归检查

- `python -m compileall src/agent.py src/company_aliases.py scripts/eval_runner.py`
- `python scripts/eval_runner.py`
- `eval/failed_cases.csv` 自动更新

## 结果说明

当前评测仍有少量边界样本（主要是中文别名识别与对比关键词覆盖）需要继续扩展词表和关键词集合。  
但“只识别到一个对比实体就报错”的体验问题已通过自动回退机制缓解。

## 下一步（Step 31）

1. 将词表从 Python 常量升级为可编辑数据文件（例如 `eval/company_aliases.csv`）并支持热更新加载；
2. 扩充失败样本驱动词表迭代流程（`failed_cases.csv` -> 别名补全）；
3. 完成一轮“中文高频口语提问”专项回归。
