# Step 39：研究 Agent 可验证第一版（V1）

## 目标

在不破坏现有 UI 和能力的前提下，完成“上市公司分析AGENT”第一版可验证闭环：

1. 项目题目升级为“上市公司分析AGENT”。
2. 深度研究报告支持一键导出 Markdown。
3. 文档与日志同步更新，保证可投递和可复盘。

## 本步实现

- 应用标题与首屏文案改为“上市公司分析AGENT”。
- `README.md` 项目名称与定位文案更新为“上市公司分析AGENT”。
- 深度研究报告区域新增导出按钮：
  - 按钮名：`导出研究报告（Markdown）`
  - 文件名：`company_research_report.md`
  - 内容覆盖：结论、经营表现、盈利质量、现金流质量、风险、证据来源、限制说明、跟踪清单。
- 导出逻辑统一封装为 `_build_research_markdown(result)`，便于后续扩展 Word/PDF。
- 新增轻量 RAG 检索：
  - `retrieve_relevant_passages(documents, query)` 按问题检索资料片段。
  - 研究摘要优先拼接命中的高相关片段，减少泛化表述。
- 补齐资料目录能力：
  - 统一接入 `data/reports`、`data/company_info`、`data/industry_info` 三类资料。
  - 在报告中展示“资料命中概览”，便于验证 RAG 是否生效。
- 新增研究图表能力：
  - 单公司深度报告增加“经营质量三指标”柱状图（收入、净利润、经营现金流）。
  - 双公司深度报告增加“核心指标对比”分组柱状图。
- 新增研究写作 skill：
  - `refine_research_result(result, query)` 对研究文本进行二次润色。
  - 有 API 时进行结构化重写，无 API 时执行本地保守优化，不中断主流程。

## 验收标准

- 应用能正常启动并进入首页。
- 首页主标题显示“上市公司分析AGENT”。
- 单公司或双公司分析完成后，“深度研究报告”区域出现导出按钮。
- 点击导出按钮后可下载 Markdown，内容包含结构化研究字段与免责声明。

## 风险与后续

- 当前导出仅支持 Markdown，暂未接 Word。
- 导出报告的图表引用和资料命中详情将在下一步补齐。
- 下一步将优先接入资料索引可视化与研究图表模块。

## Step 42 增量更新（2026-05-23）

### 新增能力

- 本地资料加载新增 `PDF` 支持（`txt/md/pdf`）。
- 新增依赖：`pypdf>=4.2.0`。
- 冒烟脚本 `scripts/smoke_check.py` 重写为 UTF-8，并修复对比失败提示校验的脆弱断言。

### 实现说明

- `src/report_loader.py`：
  - 增加 `_read_pdf_file(path)`，从 PDF 提取文本（默认最多前 30 页）。
  - 增加 `_read_content(path)`，统一处理 txt/md/pdf。
  - 资料类型命名统一为中文可读版本，避免报告展示乱码。
- `scripts/smoke_check.py`：
  - 测试查询改为可读中文。
  - 对失败提示用关键词容错匹配，降低测试误报。

### 验收预期

- 当 `data/reports` 或 `data/company_info` 放入可提取文本的 PDF 时，资料命中数量可大于 0。
- 冒烟检查可稳定返回 JSON 结果，不再出现编码字符串导致的断言失败。
