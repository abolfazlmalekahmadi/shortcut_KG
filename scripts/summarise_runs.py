#!/usr/bin/env python3
"""Collect every run summary in ``output/*.json`` into one Markdown table.

    python scripts/summarise_runs.py                 # prints to stdout
    python scripts/summarise_runs.py --out output/CROSS_DATASET.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

COLUMNS = [
    ("dataset", "dataset"),
    ("variant", "variant"),
    ("n", "n_rows"),
    ("ok", "n_quality_ok"),
    ("CTR", "ctr"),
    ("heart w", "heart_width_px"),
    ("thorax w", "thorax_width_px"),
    ("lung area", "lung_area_frac"),
    ("heart/lung area", "heart_lung_area_ratio"),
]


def best_per_dataset(paths: list[Path]) -> list[dict]:
    """One row per (dataset, variant): the run with the most rows."""
    chosen: dict[tuple[str, str], dict] = {}
    for path in paths:
        try:
            summary = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        run = summary.get("run") or {}
        key = (run.get("dataset"), run.get("variant"))
        if not all(key):
            continue
        if key not in chosen or summary["n_rows"] > chosen[key]["n_rows"]:
            summary["_path"] = str(path)
            chosen[key] = summary
    return sorted(chosen.values(), key=lambda s: (s["run"]["dataset"], s["run"]["variant"]))


def _num(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1000:
        return f"{value:,.0f}"
    if magnitude >= 10:
        return f"{value:.1f}"
    return f"{value:.3f}"


def fmt_stat(stats: dict | None) -> str:
    if not stats:
        return "—"
    mean, sd = stats.get("mean"), stats.get("sd")
    if mean is None:
        return "—"
    if sd is None:
        return _num(mean)
    return f"{_num(mean)} ± {_num(sd)}"


def to_markdown(summaries: list[dict]) -> str:
    header = "| " + " | ".join(c[0] for c in COLUMNS) + " |"
    align = "|" + "|".join(["---"] + ["---:"] * (len(COLUMNS) - 1)) + "|"
    lines = [header, align]
    for s in summaries:
        run = s["run"]
        stats = s["stats_quality_ok"]
        cells = []
        for _, key in COLUMNS:
            if key in ("dataset", "variant"):
                cells.append(str(run[key]))
            elif key in ("n_rows", "n_quality_ok"):
                cells.append(str(s[key]))
            elif key in ("ctr", "heart_lung_area_ratio"):
                st = stats.get(key)
                cells.append("—" if not st or st["mean"] is None else f"{st['mean']:.3f} ± {st['sd']:.3f}")
            elif key == "lung_area_frac":
                st = stats.get(key)
                cells.append("—" if not st or st["mean"] is None else f"{100 * st['mean']:.1f}%")
            else:
                cells.append(fmt_stat(stats.get(key)))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(
        "Statistics are computed on `quality_ok` rows only "
        "(`Dice RCA (Mean) >= 0.7`). `n` is every row read, `ok` the passing ones. "
        "Pixel widths are not comparable across datasets."
    )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--glob", default="output/*.json")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    summaries = best_per_dataset(sorted(REPO_ROOT.glob(args.glob)))
    if not summaries:
        print("no run summaries found")
        return 1
    text = to_markdown(summaries)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"wrote {args.out}  ({len(summaries)} runs)")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
