# Step 31：别名词表数据文件化

## 目标

把公司别名从代码常量升级为可编辑数据文件，降低维护成本，并支持后续失败样本驱动迭代。

## 本步改动

1. 新增词表文件  
- `eval/company_aliases.csv`  
- 字段：`alias, canonical`

2. 重构词表加载模块  
- `src/company_aliases.py`  
- 新增：
  - `load_aliases(force_reload=False)`：读取 CSV，读取失败时回退默认词表
  - 缓存机制：默认缓存一次，减少重复 IO
  - `force_reload=True` 可手动刷新缓存

3. Agent 接入动态词表  
- `src/agent.py`  
- `_extract_company_mentions` 改为每次从 `load_aliases()` 获取映射，不再依赖硬编码常量。

## 回归

- `python -m compileall src/company_aliases.py src/agent.py`
- `python scripts/eval_runner.py`

## 结果

主流程保持可用，词表维护从“改代码”变为“改 CSV”。  
后续只需追加 `eval/company_aliases.csv` 即可提升识别命中率。

## 下一步建议

Step 32：
1. 用 `eval/failed_cases.csv` 自动提示建议补充的别名；
2. 增加 `scripts/alias_check.py`，快速验证新增别名是否生效；
3. 继续收敛 compare 边界误判样本。
