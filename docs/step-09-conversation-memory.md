# Step 9 说明文档：会话上下文记忆与自动补全

## 1. 目标

解决多轮对话中“上下文不结合”的问题。  
当用户使用代词或省略公司名追问时，系统可自动继承上一轮公司上下文并继续分析。

## 2. 本步改动

- `src/models.py`
  - `AgentResult` 增加上下文字段：
    - `resolved_query`
    - `context_used`
    - `context_company_name`
    - `context_stock_code`
- `src/agent.py`
  - `run_financial_agent` 支持外部传入补全后的问题和上下文元数据
- `app.py`
  - 新增会话记忆：
    - `memory_company_name`
    - `memory_stock_code`
    - `memory_compare_pair`
  - 新增 query 补全器：支持“它/这家公司/刚才那个”等代词补全
  - 新增上下文状态条 + `清空上下文` 按钮
  - Agent trace 中展示“原始问题”和“上下文补全后问题”

## 3. 交互效果

示例：

1. 用户先问：`贵州茅台最近怎么样`
2. 再问：`它的现金流怎么样`
3. 系统会自动补全为：`贵州茅台的现金流怎么样`，并继续分析

## 4. 验收标准

- 连续追问时可继承上轮公司上下文。
- 页面可看到当前上下文公司。
- 可一键清空上下文，重置会话记忆。
