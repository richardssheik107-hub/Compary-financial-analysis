# Step 43：资料命中可解释性增强

## 目标

在不改动主流程和 UI 结构的前提下，解决“为什么资料命中是 0 不好排查”的问题。

## 本步改动

1. `src/report_loader.py`
- 在 `load_research_documents(...)` 的 `source_summary` 中新增：
  - `scanned_files`
  - `matched_files`
  - `pdf_scanned`
  - `pdf_empty`
- 通过这四项把问题分层：
  - 是否有资料文件被扫描
  - 是否有文件命中公司名/代码
  - 是否存在 PDF
  - PDF 是否提取不到文本（常见扫描版）

2. `app.py`
- “资料命中概览”新增上述 4 个统计项。
- 新增提示逻辑：当 `pdf_scanned > 0` 且 `pdf_empty > 0` 时，显示扫描版 PDF 可能无法抽取文本的告警。
- 导出 Markdown 报告同步写入这 4 个统计项，便于复盘。

## 验收标准

- 页面“资料命中概览”可看到 8 个统计项（原 4 项 + 新 4 项）。
- 若目录中有扫描版 PDF，页面出现明确提示，而不是仅显示命中为 0。
- 不影响单公司、双公司、通用问答现有流程。

## 影响范围

- 后端：`src/report_loader.py`
- 前端：`app.py`
- 依赖：无新增（沿用 Step 42 引入的 `pypdf`）
