#!/usr/bin/env python3
"""Check a finished run against the raster engine, row by row.

The full-dataset tables are written by the fast engine. This script re-derives a few of
their rows from the source CSV with the raster engine — the slow, obvious one — and
compares every measure, so a run can be trusted without re-reading all 1.2 M masks.

    python scripts/verify_run.py --csv output/full/mimic_original.csv \
        --dataset mimic --variant original --n 5

Exits non-zero on the first mismatch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from chexmask_anatomy import open_records, resolve_paths  # noqa: E402
from compute_anatomical_measures import measure_record  # noqa: E402

IDENTITY = ["dataset", "variant", "image_id", "height", "width"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--variant", default="original", choices=["original", "preprocessed"])
    p.add_argument("--n", type=int, default=5, help="how many rows to re-derive (default: 5)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    args = p.parse_args(argv)

    spec, source = resolve_paths(args.dataset, args.variant, args.data_root)
    table = pd.read_csv(args.csv)
    if not len(table):
        print(f"{args.csv}: empty")
        return 1

    indices = sorted(
        np.random.default_rng(args.seed)
        .choice(len(table), size=min(args.n, len(table)), replace=False)
        .tolist()
    )
    print(
        f"{args.csv.name}: {len(table):,} rows, {len(table.columns)} columns; "
        f"re-deriving rows {indices}"
    )

    checked = 0
    stock = set(indices)
    header, records = open_records(source, None)
    for i, record in enumerate(records):
        if i not in stock:
            continue
        expected = table.iloc[i]
        got = measure_record(header, record, spec, args.variant, "raster")
        for key in IDENTITY:
            if str(expected[key]) != str(got[key]):
                print(f"  row {i}: {key}: {expected[key]!r} != {got[key]!r}")
                return 1
        for key, value in got.items():
            if key in IDENTITY:
                continue
            want = expected[key]
            if isinstance(value, bool):
                ok = bool(want) == value
            elif isinstance(value, int):
                ok = int(want) == value
            elif pd.isna(want) and (isinstance(value, float) and np.isnan(value)):
                ok = True
            else:
                ok = np.isclose(float(want), float(value), rtol=1e-9, atol=1e-12)
            if not ok:
                print(f"  row {i}: {key}: csv {want!r} != raster {value!r}")
                return 1
        checked += 1
        stock.discard(i)
        if not stock:
            break

    if stock:
        print(f"  could not reach rows {sorted(stock)} in the source (file shorter?)")
        return 1
    print(f"  {checked} rows match the raster engine on every column")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
