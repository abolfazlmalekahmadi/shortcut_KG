#!/usr/bin/env python3
"""Compare anatomical measures computed from two runs of the same images.

Motivation: the CheXmask release ships the same annotations twice — at the source
images' native resolution (``OriginalResolution``) and padded-to-square then resized to
1024x1024 (``Preprocessed``). Measures that are ratios of an image against itself must
agree between the two; absolute pixel values must not. This script makes that check
explicit so the project can pick a variant with evidence rather than by feel.

    python scripts/compare_variants.py output/vindr_original_n200.csv \
                                        output/vindr_preprocessed_n200.csv \
                                        --key image_id
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MASK_VS_MASK = [
    "ctr",
    "ctr_same_level",
    "ctr_bbox",
    "heart_lung_area_ratio",
    "lung_width_asymmetry",
]
FRAME_NORMALISED = [
    "heart_area_frac",
    "left_lung_area_frac",
    "right_lung_area_frac",
    "lung_area_frac",
    "heart_width_norm",
    "thorax_width_norm",
    "heart_centroid_x_norm",
    "heart_centroid_y_norm",
    "lung_centroid_x_norm",
    "lung_centroid_y_norm",
    "heart_bbox_left_norm",
    "heart_bbox_top_norm",
    "heart_bbox_right_norm",
    "heart_bbox_bottom_norm",
    "lung_bbox_left_norm",
    "lung_bbox_top_norm",
    "lung_bbox_right_norm",
    "lung_bbox_bottom_norm",
    "image_aspect",
]
ABSOLUTE_PX = ["heart_width_px", "thorax_width_px", "heart_area_px", "lung_area_px"]

#: Groups and whether the two variants are *expected* to agree. ``compare`` only
#: enforces agreement on the first group.
GROUPS = (
    ("mask-vs-mask ratio (must agree)", MASK_VS_MASK),
    ("frame-normalised (may shift with padding)", FRAME_NORMALISED),
    ("absolute px (must differ)", ABSOLUTE_PX),
)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("left", type=Path)
    p.add_argument("right", type=Path)
    p.add_argument("--key", default="image_id")
    p.add_argument("--label-left", default=None)
    p.add_argument("--label-right", default=None)
    return p.parse_args(argv)


def compare(left: pd.DataFrame, right: pd.DataFrame, key: str, na: str, nb: str) -> pd.DataFrame:
    a = left.set_index(key)
    b = right.set_index(key)
    if not a.index.is_unique or not b.index.is_unique:
        # A join on a non-unique key would multiply rows; keep the first row per id.
        print(f"note: '{key}' is not unique in one of the runs; keeping the first row per id")
        a = a[~a.index.duplicated(keep="first")]
        b = b[~b.index.duplicated(keep="first")]
    common = a.index.intersection(b.index)
    a, b = a.loc[common], b.loc[common]

    rows = []
    for name, cols in GROUPS:
        for c in cols:
            if c not in a.columns or c not in b.columns:
                continue
            x, y = a[c].astype(float), b[c].astype(float)
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() < 3:
                continue
            x, y = x[ok], y[ok]
            rel = (y - x) / x.replace(0, np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                r = np.corrcoef(x, y)[0, 1]
            rows.append(
                {
                    "group": name,
                    "measure": c,
                    "n": int(ok.sum()),
                    "pearson_r": None if not np.isfinite(r) else round(float(r), 4),
                    "mean_abs_rel_diff": round(float(rel.abs().mean()), 4),
                    "p99_abs_rel_diff": round(float(rel.abs().quantile(0.99)), 4),
                    "mean_a": round(float(x.mean()), 4),
                    "mean_b": round(float(y.mean()), 4),
                }
            )
    out = pd.DataFrame(rows)
    out.attrs["n_common_images"] = len(common)
    out.attrs["labels"] = (na, nb)
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    left = pd.read_csv(args.left)
    right = pd.read_csv(args.right)
    na = args.label_left or args.left.stem
    nb = args.label_right or args.right.stem
    table = compare(left, right, args.key, na, nb)

    print(f"A = {na}\nB = {nb}\nimages in common: {table.attrs['n_common_images']}\n")
    with pd.option_context("display.width", 220, "display.max_columns", 50):
        print(table.to_string(index=False))

    enforced = table[table["group"] == GROUPS[0][0]]
    bad = enforced[enforced["mean_abs_rel_diff"] > 0.01]
    print()
    if bad.empty:
        print(
            f"OK: every mask-vs-mask ratio agrees to within 1% "
            f"(worst {enforced['mean_abs_rel_diff'].max():.4%} mean relative difference)."
        )
    else:
        print("CHECK: these mask-vs-mask measures drifted by more than 1% — the variants"
              " are not interchangeable for them:")
        print(bad.to_string(index=False))
        return 1

    frame = table[table["group"] == GROUPS[1][0]]
    if not frame.empty:
        print(
            "note: frame-normalised measures shift between variants by "
            f"{frame['mean_abs_rel_diff'].min():.1%}-{frame['mean_abs_rel_diff'].max():.1%}"
            " (Preprocessed pads images to a square before resizing), so they are only"
            " comparable within one variant."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
