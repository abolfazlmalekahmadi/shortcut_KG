#!/usr/bin/env python3
"""How much of "which dataset is this?" is already in the anatomy?

The measurement step gives every image a small vector of anatomy: CTR, heart/lung area
ratio, lung area, position inside the frame. If a trivial classifier can tell two
datasets apart from that vector alone, then a label correlated with the centre inherits
the same signal — which is the thing E2 is looking for, and the floor any cross-dataset
fairness work has to sit above.

This does **not** show that the anatomy difference is an artifact. Two datasets can differ
in age, sex and disease mix and therefore in real heart size. It measures how large the
centre-level component is, in a unit (AUC) that can be compared against the label
performance of whatever model comes later.

    python scripts/dataset_leakage.py --out output/DATASET_LEAKAGE.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

FEATURES = [
    "ctr",
    "ctr_same_level",
    "ctr_bbox",
    "heart_lung_area_ratio",
    "lung_width_asymmetry",
    "lung_area_frac",
    "heart_width_norm",
    "thorax_width_norm",
    "heart_centroid_x_norm",
    "heart_centroid_y_norm",
    "lung_centroid_x_norm",
    "lung_centroid_y_norm",
    "heart_bbox_left_norm",
    "heart_bbox_right_norm",
    "lung_bbox_left_norm",
    "lung_bbox_right_norm",
    "image_aspect",
]

#: Feature sets to compare. ``invariant`` holds only ratios of the mask against itself,
#: which survive any isotropic rescaling and any change of frame — so a dataset that the
#: classifier can name from these alone is named by its anatomy, not by its file format.
FEATURE_SETS = {
    "all": FEATURES,
    "frame-invariant": [
        "ctr",
        "ctr_same_level",
        "ctr_bbox",
        "heart_lung_area_ratio",
        "lung_width_asymmetry",
    ],
    "ctr only": ["ctr"],
}


def load(directory: Path, datasets: list[str], variant: str, per_dataset: int, seed: int):
    rng = np.random.default_rng(seed)
    parts = []
    for name in datasets:
        path = directory / f"{name}_{variant}.csv"
        df = pd.read_csv(path, usecols=["quality_ok"] + FEATURES)
        df = df[df.quality_ok].dropna(subset=FEATURES)
        if len(df) > per_dataset:
            df = df.iloc[np.sort(rng.choice(len(df), per_dataset, replace=False))]
        frame = df[FEATURES].astype(float).copy()
        frame["dataset"] = name
        parts.append(frame)
        print(f"  {name:11} {len(frame):>7,} images")
    return pd.concat(parts, ignore_index=True)


def auc_pair(table: pd.DataFrame, a: str, b: str, features: list[str], folds: int, seed: int) -> float:
    """Cross-validated AUC for telling ``a`` from ``b`` from the given features."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    part = table[table.dataset.isin([a, b])]
    x = part[features].to_numpy(dtype=float)
    y = (part.dataset == b).to_numpy()

    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    scores = []
    for train, test in skf.split(x, y):
        model = make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)
        ).fit(x[train], y[train])
        scores.append(roc_auc_score(y[test], model.predict_proba(x[test])[:, 1]))
    return float(np.mean(scores))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, default=REPO_ROOT / "output" / "full")
    p.add_argument("--variant", default="original", choices=["original", "preprocessed"])
    p.add_argument("--datasets", nargs="*", default=["mimic", "chexpert", "chestxray8", "padchest"])
    p.add_argument("--per-dataset", type=int, default=20_000)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    print("sampling:")
    table = load(args.dir, args.datasets, args.variant, args.per_dataset, args.seed)

    pairs = [
        (a, b) for i, a in enumerate(args.datasets) for b in args.datasets[i + 1 :]
    ]
    names = list(FEATURE_SETS)
    lines = [
        "# How much of the centre is in the anatomy?",
        "",
        "Cross-validated AUC of telling two datasets apart from the anatomy alone — no",
        "image, no model beyond a logistic regression, no metadata. Columns differ only in",
        f"which of the {len(FEATURES)} measures they may use; `{args.variant}` grids,",
        f"{args.per_dataset:,} random quality-ok images per dataset, {args.folds}-fold",
        "stratified CV.",
        "",
        "| pair | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
    ]
    for a, b in pairs:
        scores = []
        for name in names:
            scores.append(auc_pair(table, a, b, FEATURE_SETS[name], args.folds, args.seed))
        print(f"  {a:11} vs {b:11} " + "  ".join(f"{n}={s:.3f}" for n, s in zip(names, scores)))
        lines.append(f"| {a} vs {b} | " + " | ".join(f"{s:.3f}" for s in scores) + " |")
    lines.append("")
    lines.append(
        "`frame-invariant` uses only ratios of a mask against itself, so it survives any\n"
        "rescaling and any change of frame: a dataset named from those alone is named by\n"
        "its anatomy rather than by its file format. `all` additionally uses the frame,\n"
        "which is where ChestX-Ray8's 1024x1024 padding gives itself away.\n"
        "\n"
        "AUC near 0.5 means the anatomy does not know the dataset, near 1.0 that it does.\n"
        "This is a centre-level signal sitting in measurements that need no image and no\n"
        "model, so any label correlated with the centre inherits it. It is not by itself\n"
        "evidence of an artifact: age, sex and disease mix differ between these datasets and\n"
        "would legitimately move heart size. Separating those needs the acquisition and\n"
        "demographic columns, which is the next step of E1."
    )
    text = "\n".join(lines) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
