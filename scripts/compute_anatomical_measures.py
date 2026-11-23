#!/usr/bin/env python3
"""Compute per-image anatomical measures from CheXmask masks.

First step of E1 in the project brief: heart width, lung areas and cardiothoracic ratio,
as a CSV that can later be joined into the per-image knowledge graph.

Two engines, same numbers:

``fast`` (default)
    Reads the measures straight out of the run-length encoding
    (:mod:`chexmask_anatomy.measures_rle`). ~1500 rows/s at native resolution. This is
    what the full-dataset runs use.
``raster``
    Decodes the masks to pixel arrays first (:mod:`chexmask_anatomy.measures`). ~3 rows/s
    at native resolution; short and obviously correct, kept as the reference that
    ``tests/test_fast_engine.py`` checks the fast engine against.

The whole file is processed as a stream, so ``--n`` can be omitted to do every row
without loading the CSV into memory.

Examples
--------
    # a 200-image subset of VinDr-CXR at native resolution, plus an overlay figure
    python scripts/compute_anatomical_measures.py --dataset vindr --n 200 --plot 4

    # every MIMIC-CXR-JPG image, from the fixed 1024x1024 grids
    python scripts/compute_anatomical_measures.py --dataset mimic --variant preprocessed

    # check the two engines agree on this subset
    python scripts/compute_anatomical_measures.py --dataset vindr --n 50 --engine raster
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chexmask_anatomy import (  # noqa: E402
    MASK_COLUMNS,
    decode_rle,
    measure_masks,
    measure_rle,
    open_records,
    resolve_paths,
)

DEFAULT_DATA_ROOT = REPO_ROOT / "data"
DEFAULT_OUT_DIR = REPO_ROOT / "output"

FRONT_COLUMNS = [
    "dataset",
    "variant",
    "image_id",
    "height",
    "width",
    "quality_ok",
    "dice_rca_mean",
    "dice_rca_max",
]

SUMMARY_MEASURES = [
    "heart_width_px",
    "heart_width_norm",
    "thorax_width_px",
    "thorax_width_norm",
    "ctr",
    "ctr_same_level",
    "ctr_bbox",
    "heart_area_frac",
    "left_lung_area_frac",
    "right_lung_area_frac",
    "lung_area_frac",
    "heart_lung_area_ratio",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", required=True, help="vindr | chexpert | mimic | padchest | chestxray8")
    p.add_argument(
        "--variant",
        default="original",
        choices=["original", "preprocessed"],
        help="which CheXmask grid to use (default: original)",
    )
    p.add_argument("--n", type=int, default=200, help="how many images; 0 = every row")
    p.add_argument("--sample", default="first", choices=["first", "random"])
    p.add_argument("--seed", type=int, default=0, help="seed for --sample random")
    p.add_argument(
        "--scan",
        type=int,
        default=50_000,
        help="for --sample random: draw from the first SCAN records only (default: 50000)",
    )
    p.add_argument("--engine", default="fast", choices=["fast", "raster"])
    p.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    p.add_argument("--out", type=Path, default=None, help="output CSV path")
    p.add_argument(
        "--min-dice",
        type=float,
        default=None,
        help="skip rows whose Dice RCA (Mean) is below this (CheXmask suggests 0.7)",
    )
    p.add_argument("--plot", type=int, default=0, help="write an overlay figure of the first N images")
    p.add_argument("--tag", default=None, help="name for the outputs (default: dataset_variant_n)")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args(argv)


def _float_or_nan(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def measure_record(header: list[str], record: list[str], spec, variant: str, engine: str) -> dict:
    """Decode one CSV record and return its measures, in a stable column order."""
    row = dict(zip(header, record))
    height, width = int(row["Height"]), int(row["Width"])
    if engine == "fast":
        values = measure_rle(row["Heart"], row["Left Lung"], row["Right Lung"], height, width)
    else:
        values = measure_masks(
            decode_rle(row["Heart"], height, width) > 0,
            decode_rle(row["Left Lung"], height, width) > 0,
            decode_rle(row["Right Lung"], height, width) > 0,
        )
    dice_mean = _float_or_nan(row["Dice RCA (Mean)"])
    front = {
        "dataset": spec.key,
        "variant": variant,
        "image_id": row[spec.id_column],
        "height": height,
        "width": width,
        "quality_ok": bool(dice_mean >= 0.7),
        "dice_rca_mean": dice_mean,
        "dice_rca_max": _float_or_nan(row["Dice RCA (Max)"]),
    }
    front.update(values)
    return front


def summarise(df: pd.DataFrame) -> dict:
    """Mean / sd / median / IQR for the headline measures, over quality-passing rows."""
    heart = df[df["quality_ok"]]
    summary: dict = {
        "n_rows": int(len(df)),
        "n_quality_ok": int(heart.shape[0]),
        "n_quality_fail": int(len(df) - heart.shape[0]),
    }
    stats = {}
    for k in SUMMARY_MEASURES:
        if k not in df.columns:
            continue
        s = heart[k].astype(float)
        finite = int(np.isfinite(s).sum())
        stats[k] = {
            "mean": _round(s.mean()) if finite else None,
            "sd": _round(s.std(ddof=1)) if finite > 1 else None,
            "median": _round(s.median()) if finite else None,
            "p05": _round(s.quantile(0.05)) if finite else None,
            "p95": _round(s.quantile(0.95)) if finite else None,
            "min": _round(s.min()) if finite else None,
            "max": _round(s.max()) if finite else None,
            "n_finite": finite,
        }
    summary["stats_quality_ok"] = stats
    if "image_aspect" in df.columns:
        summary["image_aspect"] = {
            "min": _round(df["image_aspect"].min()),
            "median": _round(df["image_aspect"].median()),
            "max": _round(df["image_aspect"].max()),
        }
    if "lung_touches_border" in df.columns:
        summary["lung_touches_border_n"] = int(df["lung_touches_border"].sum())
    return summary


def _round(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else round(f, 6)


def iter_measures(header, records, spec, variant, engine, min_dice=None, progress=None):
    """Yield one measures dict per record, skipping rows below ``min_dice``."""
    for i, record in enumerate(records):
        values = measure_record(header, record, spec, variant, engine)
        if progress is not None:
            progress(i)
        if min_dice is not None and not (values["dice_rca_mean"] >= min_dice):
            continue
        yield values


def plot_examples(header, records, spec, engine: str, out_path: Path) -> None:
    """Overlay the decoded masks of the first few rows, for a visual sanity check."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    records = list(records)
    n = min(len(records), 4)
    records = records[:n]
    cols = max(1, n)
    fig, axes = plt.subplots(1, cols, figsize=(3.1 * cols, 4.0), squeeze=False)

    for ax, record in zip(axes.ravel(), records):
        row = dict(zip(header, record))
        h, w = int(row["Height"]), int(row["Width"])
        heart = decode_rle(row["Heart"], h, w) > 0
        left = decode_rle(row["Left Lung"], h, w) > 0
        right = decode_rle(row["Right Lung"], h, w) > 0
        me = measure_rle(row["Heart"], row["Left Lung"], row["Right Lung"], h, w)
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[..., 0] = right * 255  # patient's right lung -> red
        canvas[..., 1] = left * 255  # patient's left  lung -> green
        canvas[..., 2] = heart * 255  # heart -> blue
        ax.imshow(canvas)
        # CheXpert ids are paths whose file name is identical for every image
        # ("view1_frontal.jpg"); keep the last few path components instead.
        parts = [p for p in row[spec.id_column].replace("\\", "/").split("/") if p]
        ident = "/".join(parts[-3:]) if len(parts) >= 3 else row[spec.id_column]
        ax.set_title(
            f"{ident[:26]}\n{w}x{h} px · heart {me['heart_width_px']} · CTR {me['ctr']:.2f}",
            fontsize=7,
        )
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle(
        f"{spec.label} · {Path(out_path).stem} · red = right lung, green = left lung, blue = heart",
        fontsize=9,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    t0 = time.time()
    log = (lambda *a: None) if args.quiet else print

    spec, path = resolve_paths(args.dataset, args.variant, args.data_root)
    total = None if args.n in (0, None) else args.n
    tag = args.tag or f"{args.dataset}_{args.variant}" + (f"_n{args.n}" if total else "_all")
    out_csv = args.out or (DEFAULT_OUT_DIR / f"{tag}.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    log(f"[1/4] {spec.label} · {args.variant} · {path.name}  ({path.stat().st_size / 2**30:.1f} GiB)"
        f" · engine={args.engine} · {'all rows' if total is None else f'{total} rows'}")

    header, records = open_records(
        path, total, sample=args.sample, seed=args.seed, scan=args.scan
    )

    def progress(i: int) -> None:
        if not args.quiet and (i + 1) % 25_000 == 0:
            print(f"      {i + 1:,} rows  ({time.time() - t0:.0f}s)", flush=True)

    columns = FRONT_COLUMNS
    n_written = 0
    partial = out_csv.with_suffix(out_csv.suffix + ".partial")
    with open(partial, "w", newline="") as fh:
        writer = None
        for values in iter_measures(
            header, records, spec, args.variant, args.engine, args.min_dice, progress
        ):
            if writer is None:
                columns = list(values)
                writer = csv.DictWriter(fh, fieldnames=columns)
                writer.writeheader()
            writer.writerow(values)
            n_written += 1
        if writer is None:  # nothing survived the filters
            fh.write(",".join(columns) + "\n")
    # Rename only once the file is complete, so a crash cannot leave a truncated table
    # that later runs would mistake for a finished one.
    os.replace(partial, out_csv)
    log(f"[2/4] wrote {out_csv}  ({n_written:,} rows x {len(columns)} cols)"
        f"  ({time.time() - t0:.0f}s)")

    df = pd.read_csv(out_csv)
    summary = summarise(df)
    summary["run"] = {
        "command": " ".join(["python", "scripts/compute_anatomical_measures.py"] + list(argv or sys.argv[1:])),
        "dataset": spec.key,
        "variant": args.variant,
        "engine": args.engine,
        "source_file": str(path),
        "source_bytes": path.stat().st_size,
        "sample": args.sample,
        "seed": args.seed if args.sample == "random" else None,
        "requested_n": total,
        "min_dice": args.min_dice,
        "rows_per_second": round(n_written / max(time.time() - t0, 1e-9), 1),
        "cwd": str(Path.cwd()),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "git_commit": _git_commit(),
        "elapsed_seconds": round(time.time() - t0, 1),
        "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out_json = out_csv.with_suffix(".json")
    out_json.write_text(json.dumps(summary, indent=2) + "\n")
    log(f"[3/4] wrote {out_json}")

    st = summary["stats_quality_ok"]
    log(
        "\nheadline (quality-ok rows, n={:,} of {:,}):\n"
        "  CTR        {:>10}\n"
        "  heart w    {:>10}\n"
        "  thorax w   {:>10}\n"
        "  lung area  {:>10}".format(
            summary["n_quality_ok"], summary["n_rows"],
            _fmt(st["ctr"]["mean"], st["ctr"]["sd"]),
            _fmt(st["heart_width_px"]["mean"], st["heart_width_px"]["sd"]),
            _fmt(st["thorax_width_px"]["mean"], st["thorax_width_px"]["sd"]),
            _fmt(st["lung_area_frac"]["mean"], st["lung_area_frac"]["sd"]),
        )
    )

    if args.plot:
        fig_path = DEFAULT_OUT_DIR / "figures" / f"{tag}.png"
        # re-read just the first few source records for the figure
        header2, recs2 = open_records(path, args.plot, sample="first")
        plot_examples(header2, list(recs2), spec, args.engine, fig_path)
        log(f"[4/4] wrote {fig_path}")
    return 0


def _fmt(mean, sd) -> str:
    if mean is None:
        return "—"
    if sd is None:
        return f"{mean:g}"
    return f"{mean:g} ± {sd:g}"


def _git_commit() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
