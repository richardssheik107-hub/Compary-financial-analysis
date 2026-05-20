# Step 8 说明文档：统一追问建议输出

## 1. 目标

让用户在任意问题场景下都能获得“下一步可问什么”的清晰输出，避免对话中断。

## 2. 本步改动

- `src/models.py`
  - `AgentResult` 新增 `suggested_questions: list[str]`
- `src/agent.py`
  - 新增 `_build_general_followups(...)`
  - 在通用问答、单公司、双公司、失败提示场景中统一返回追问建议
- `app.py`
  - 新增 `render_suggested_questions(agent_result)`
  - 统一展示“你可以继续这样问”卡片，并支持一键 `追问`

## 3. 效果

- 通用问题：给出方法论类追问建议
- 单公司问题：给出该公司的深入分析追问建议
- 双公司问题：给出对比深化追问建议
- 识别失败问题：仍提供示例问题引导用户继续提问

## 4. 验收标准

- 三类核心场景都返回 `suggested_questions`
- 页面可见“你可以继续这样问”区块，并可点击触发追问
