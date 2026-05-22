# Step 32：别名运维工具化（检查 + 建议）

## 目标

把“失败样本修别名”从手工排查升级为可重复的小工具流程，提升迭代效率。

## 本步改动

1. 修复词表文件编码与坏行  
- 文件：`eval/company_aliases.csv`  
- 处理：重建为干净 UTF-8 内容，修复异常行。

2. 新增别名生效检查脚本  
- 文件：`scripts/alias_check.py`  
- 用法：
  - `python scripts/alias_check.py 万科`
  - `python scripts/alias_check.py 招行 --reload`
- 输出：
  - CSV 映射结果
  - `identify_company` 是否识别成功、识别到的公司与代码

3. 新增失败样本别名建议脚本  
- 文件：`scripts/alias_suggest.py`  
- 用法：`python scripts/alias_suggest.py`
- 输出：从 `eval/failed_cases.csv` 中提取的候选 alias 列表，方便追加到词表。

## 回归

- `python -m compileall scripts/alias_check.py scripts/alias_suggest.py src/company_aliases.py`
- `python scripts/alias_check.py 万科 --reload`
- `python scripts/alias_suggest.py`

## 下一步建议

Step 33：
1. `alias_suggest.py` 直接输出可追加到 CSV 的模板文件；
2. 建立“新增别名 -> alias_check -> eval_runner”一键流程；
3. 针对 compare 边界样本继续规则收敛。
