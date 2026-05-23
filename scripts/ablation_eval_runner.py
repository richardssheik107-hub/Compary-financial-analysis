from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"


def _run_mode(mode: str, limit: int, offline: bool) -> tuple[Path, Path]:
    out_csv = EVAL_DIR / f"text_quality_{mode}.csv"
    out_md = EVAL_DIR / f"text_quality_{mode}.md"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "text_quality_eval_runner.py"),
        "--mode",
        mode,
        "--limit",
        str(limit),
        "--label",
        f"{mode}-offline-{limit}" if offline else f"{mode}-{limit}",
        "--out-csv",
        str(out_csv),
        "--out-md",
        str(out_md),
    ]
    if offline:
        cmd.append("--offline")
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    return out_csv, out_md


def _summary_from_csv(path: Path) -> dict[str, float]:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    total = len(rows) or 1

    def rate(key: str, true_value: str = "True") -> float:
        return sum(1 for r in rows if str(r.get(key)) == true_value) / total

    def avg(key: str) -> float:
        return sum(float(r.get(key) or 0) for r in rows) / total

    return {
        "route_success_rate": rate("route_ok"),
        "structure_pass_rate": sum(1 for r in rows if float(r.get("structure_score") or 0) >= 18) / total,
        "evidence_coverage_rate": rate("source_used"),
        "text_quality_pass_rate": rate("quality_pass"),
        "empty_talk_rate": rate("empty_talk"),
        "logic_issue_rate": rate("logic_issue"),
        "avg_total_score": avg("total_score"),
        "avg_answer_length": avg("answer_length"),
        "avg_source_count": avg("source_count"),
    }


def _write_table(table_path: Path, summaries: dict[str, dict[str, float]], limit: int, offline: bool) -> None:
    def pct(v: float) -> str:
        return f"{v * 100:.2f}%"

    lines = [
        f"# 消融实验结果（{'offline' if offline else 'online'}，N={limit}）",
        "",
        "| 指标 | Base | Base + RAG | Base + RAG + Skill |",
        "|---|---:|---:|---:|",
    ]
    metrics = [
        "route_success_rate",
        "structure_pass_rate",
        "evidence_coverage_rate",
        "text_quality_pass_rate",
        "empty_talk_rate",
        "logic_issue_rate",
    ]
    for key in metrics:
        lines.append(
            f"| {key} | {pct(summaries['base'][key])} | {pct(summaries['base_rag'][key])} | {pct(summaries['full'][key])} |"
        )
    lines.extend(
        [
            f"| avg_total_score | {summaries['base']['avg_total_score']:.1f} | {summaries['base_rag']['avg_total_score']:.1f} | {summaries['full']['avg_total_score']:.1f} |",
            f"| avg_answer_length | {summaries['base']['avg_answer_length']:.1f} | {summaries['base_rag']['avg_answer_length']:.1f} | {summaries['full']['avg_answer_length']:.1f} |",
            f"| avg_source_count | {summaries['base']['avg_source_count']:.1f} | {summaries['base_rag']['avg_source_count']:.1f} | {summaries['full']['avg_source_count']:.1f} |",
            "",
            "## 文件产物",
            "",
            "- `eval/text_quality_base.csv`",
            "- `eval/text_quality_base_rag.csv`",
            "- `eval/text_quality_full.csv`",
        ]
    )
    table_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ablation evaluation for base/base_rag/full.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--out-md", default=str(EVAL_DIR / "ablation_summary.md"))
    args = parser.parse_args()

    mode_csv = {}
    for mode in ["base", "base_rag", "full"]:
        csv_path, _ = _run_mode(mode, args.limit, args.offline)
        mode_csv[mode] = csv_path

    summaries = {mode: _summary_from_csv(path) for mode, path in mode_csv.items()}
    out_md = Path(args.out_md)
    _write_table(out_md, summaries, args.limit, args.offline)
    print(f"wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
