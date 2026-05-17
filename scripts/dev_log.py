from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "dev_logs"


def build_template(today: str) -> str:
    return f"""# {today} 开发日志

## 今日完成

- 待填写

## 当前待办

- 待填写

## 风险与阻塞

- 暂无

## 下一步建议

- 待填写
"""


def append_items(path: Path, done: list[str], todo: list[str]) -> None:
    if not done and not todo:
        return

    lines = ["", "## 本次追加", ""]
    if done:
        lines.append("### 完成事项")
        lines.extend(f"- {item}" for item in done)
        lines.append("")
    if todo:
        lines.append("### 待办事项")
        lines.extend(f"- {item}" for item in todo)
        lines.append("")
    path.write_text(path.read_text(encoding="utf-8") + "\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update today's development log.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Log date, format YYYY-MM-DD.")
    parser.add_argument("--done", action="append", default=[], help="Completed development item. Can be used multiple times.")
    parser.add_argument("--todo", action="append", default=[], help="Todo item. Can be used multiple times.")
    args = parser.parse_args()

    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{args.date}.md"
    if not log_path.exists():
        log_path.write_text(build_template(args.date), encoding="utf-8")
    append_items(log_path, args.done, args.todo)
    print(log_path)


if __name__ == "__main__":
    main()
