#!/usr/bin/env python3
"""比较两次固定评测运行，并生成版本对照报告。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def fmt(value: Any, percent: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}%" if percent else f"{float(value):.2f}"


def delta(old: Any, new: Any, percent: bool = False, lower_is_better: bool = False) -> str:
    if old is None or new is None:
        return "N/A"
    difference = float(new) - float(old)
    if percent:
        improvement = -difference if lower_is_better else difference
        if abs(improvement) < 0.0000005:
            improvement = 0.0
        return f"{improvement * 100:+.1f} 个百分点"
    if lower_is_better and float(old) != 0:
        improvement = (float(old) - float(new)) / float(old)
        if abs(improvement) < 0.0000005:
            improvement = 0.0
        return f"{improvement * 100:+.1f}%"
    return f"{difference:+.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="比较两次今日宜食评测报告")
    parser.add_argument("baseline", type=Path, help="旧版本 summary.json")
    parser.add_argument("candidate", type=Path, help="新版本 summary.json")
    parser.add_argument("--output", type=Path, default=Path("evaluation/reports/comparison.md"))
    args = parser.parse_args()
    old = read(args.baseline)
    new = read(args.candidate)
    old_hash = nested(old, "metadata", "caseFileSha256")
    new_hash = nested(new, "metadata", "caseFileSha256")
    if old_hash != new_hash:
        raise SystemExit("拒绝比较：两份报告使用的评测集 SHA-256 不同")
    for snapshot_key, label in (
        ("slotOptionsSha256", "槽位字典"),
        ("publicMealsSha256", "公共餐食库"),
        ("configFileSha256", "评测配置"),
        ("faultCaseFileSha256", "故障评测集"),
    ):
        if nested(old, "metadata", snapshot_key) != nested(new, "metadata", snapshot_key):
            raise SystemExit(f"拒绝比较：两份报告使用的{label}快照不同")
    old_repeats = nested(old, "metadata", "repeats")
    new_repeats = nested(new, "metadata", "repeats")
    if old_repeats != new_repeats:
        raise SystemExit("拒绝比较：两份报告的重复次数不同")

    specs = [
        ("最终意图 Accuracy", ("quality", "finalIntent", "accuracy"), True, False),
        ("最终意图 Macro-F1", ("quality", "finalIntent", "macroF1"), False, False),
        ("最终槽位 Micro-F1", ("quality", "finalSlots", "microF1"), False, False),
        ("澄清决策 Accuracy", ("quality", "clarify", "accuracy"), True, False),
        ("Hit@3", ("quality", "retrieval", "hitAt3"), True, False),
        ("常规样本原始候选越界率", ("quality", "retrieval", "regularCases", "rawViolationRate"), True, True),
        ("红队样本原始候选越界率", ("quality", "retrieval", "redTeamCases", "rawViolationRate"), True, True),
        ("Fallback Rate", ("quality", "fallback", "triggerRate"), True, True),
        ("端到端 P50/ms", ("quality", "performance", "latencyMs", "p50"), False, True),
        ("端到端 P95/ms", ("quality", "performance", "latencyMs", "p95"), False, True),
        ("平均总 Token", ("quality", "performance", "totalTokens", "mean"), False, True),
        ("P95 总 Token", ("quality", "performance", "totalTokens", "p95"), False, True),
    ]
    lines = [
        "# 旧版本 / 新版本固定评测对照",
        "",
        f"- Baseline：`{nested(old, 'metadata', 'runName')}`",
        f"- Candidate：`{nested(new, 'metadata', 'runName')}`",
        f"- 评测集 SHA-256：`{old_hash}`",
        f"- 重复次数：`{old_repeats}`",
        "",
        "| 指标 | Baseline | Candidate | 改善（正数更优） |",
        "|---|---:|---:|---:|",
    ]
    for label, path, is_percent, lower_is_better in specs:
        old_value = nested(old, *path)
        new_value = nested(new, *path)
        lines.append(
            f"| {label} | {fmt(old_value, is_percent)} | {fmt(new_value, is_percent)} | "
            f"{delta(old_value, new_value, is_percent, lower_is_better)} |"
        )
    lines.extend([
        "",
        "> 正数表示 Candidate 更优，负数表示退化。延迟与 Token 使用相对下降比例；准确率和 Fallback Rate 使用百分点。",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
