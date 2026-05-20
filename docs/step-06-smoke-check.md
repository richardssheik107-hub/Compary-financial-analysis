# Step 6 说明文档：一键冒烟回归脚本

## 1. 目标

提供一个可重复执行的最小回归脚本，帮助每次改动后快速确认主链路未回归。

## 2. 脚本位置

- `scripts/smoke_check.py`

## 3. 覆盖场景

1. Streamlit 健康检查（默认 `http://localhost:8502/_stcore/health`）
2. 单公司分析链路（`贵州茅台`）
3. 双公司对比链路（`宁德时代和比亚迪谁更好`）
4. 对比失败提示链路（`A和B谁更好`）

## 4. 使用方式

默认执行：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_check.py
```

指定端口：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_check.py --port 8502
```

只跑 Agent 流程（跳过健康检查）：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_check.py --skip-health
```

## 5. 输出说明

- 输出 JSON 摘要，包含每项检查的 `passed` 和 `detail`。
- 任一检查失败时，进程退出码为 `1`。
- 全部通过时，进程退出码为 `0`。

## 6. 适用边界

- 该脚本是冒烟检查，不替代完整 UI 手工验收。
- 对比场景结论内容会随实时数据变化，但结构完整性应保持稳定。
