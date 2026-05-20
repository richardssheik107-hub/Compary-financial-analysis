# Step 12 说明文档：会话上下文存储结构标准化

## 1. 目标

把散落在 `session_state` 的上下文字段收敛为统一结构，降低后续迭代复杂度与状态不一致风险。

## 2. 本步改动

- 新增 `src/context_store.py`
  - `ConversationContext`：
    - `company_name`
    - `stock_code`
    - `compare_pair`
    - `last_intent`
    - `last_query`
    - `last_resolved_query`
  - `context_from_state(raw)`：容错读取与反序列化
- 更新 `app.py`
  - 统一使用 `st.session_state["conversation_context"]`
  - `run_query` 中统一更新上下文
  - `render_context_bar` 改为读取标准结构
  - `清空上下文` 改为重置标准结构
  - 保留旧键迁移（首次进入自动迁移 `memory_*`）

## 3. 验收标准

- 会话内上下文读写只通过 `conversation_context` 完成。
- 原有上下文能力不回归（代词补全、上下文状态条、清空上下文）。
- 冒烟回归通过。
