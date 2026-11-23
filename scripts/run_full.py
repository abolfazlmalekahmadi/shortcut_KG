#!/usr/bin/env python3
"""Run the anatomical measures over every row of every CheXmask dataset.

Nine passes: the five ``OriginalResolution`` CSVs and the four ``Preprocessed`` ones
(``ChestX-Ray8`` has no preprocessed raster). Each pass streams its CSV, so memory stays
flat however many rows it has.

    python scripts/run_full.py                 # all of them, 4 at a time
    python scripts/run_full.py --datasets vindr mimic --variant original
    python scripts/run_full.py --list          # show the nine passes and their sizes

Outputs land in ``output/full/<dataset>_<variant>.csv`` with a ``.json`` summary beside
each, and one log per pass in ``output/full/logs/``. The CSVs are large and are not meant
to be committed; the JSON summaries are small and are.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chexmask_anatomy import DATASETS, resolve_paths  # noqa: E402

CLI = REPO_ROOT / "scripts" / "compute_anatomical_measures.py"

DEFAULT_DATASETS = ["vindr", "chexpert", "mimic", "padchest", "chestxray8"]
DEFAULT_VARIANTS = ["original", "preprocessed"]


def passes_for(datasets: list[str], variants: list[str], data_root: Path) -> list[tuple[str, str, Path]]:
    out = []
    for dataset in datasets:
        for variant in variants:
            try:
                spec, path = resolve_paths(dataset, variant, data_root)
            except (FileNotFoundError, ValueError):
                continue
            out.append((dataset, variant, path))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datasets", nargs="*", default=DEFAULT_DATASETS)
    p.add_argument("--variant", nargs="*", default=DEFAULT_VARIANTS, choices=DEFAULT_VARIANTS)
    p.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "output" / "full")
    p.add_argument("--jobs", type=int, default=4, help="passes to run at once (default: 4)")
    p.add_argument("--list", action="store_true", help="print the passes and exit")
    p.add_argument("--force", action="store_true", help="redo passes whose output already exists")
    args = p.parse_args(argv)

    work = passes_for(args.datasets, args.variant, args.data_root)
    if not work:
        print("no passes to run")
        return 1

    if args.list:
        total = 0
        for dataset, variant, path in work:
            size = path.stat().st_size / 2**30
            total += size
            print(f"  {dataset:11} {variant:13} {size:6.1f} GiB  {path.name}")
        print(f"  {'':11} {'TOTAL':13} {total:6.1f} GiB")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "logs").mkdir(exist_ok=True)
    t0 = time.time()

    skipped = 0
    pending = []
    for dataset, variant, path in work:
        exe = args.out_dir / f"{dataset}_{variant}.csv"
        if exe.exists() and not args.force:
            print(f"skip {exe.name} (exists; --force to redo)")
            skipped += 1
            continue
        pending.append((dataset, variant, path))

    running: list[tuple[subprocess.Popen, str, Path]] = []
    done = 0

    def start(item) -> None:
        dataset, variant, path = item
        log = open(args.out_dir / "logs" / f"{dataset}_{variant}.log", "w")
        proc = subprocess.Popen(
            [
                sys.executable,
                str(CLI),
                "--dataset", dataset,
                "--variant", variant,
                "--n", "0",
                "--tag", f"{dataset}_{variant}",
                "--out", str(args.out_dir / f"{dataset}_{variant}.csv"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=REPO_ROOT,
        )
        print(f"start {dataset}_{variant}  ({path.stat().st_size / 2**30:.1f} GiB)")
        running.append((proc, f"{dataset}_{variant}", log))

    item_iter = iter(pending)
    while len(running) < args.jobs:
        try:
            start(next(item_iter))
        except StopIteration:
            break

    while running:
        proc, name, log = running[0]
        code = proc.wait()
        log.close()
        running.pop(0)
        if code == 0:
            done += 1
            print(f"  ok   {name}  ({time.time() - t0:.0f}s elapsed)")
        else:
            print(f"  FAIL {name} exit={code} — see {args.out_dir / 'logs' / (name + '.log')}")
            return 1
        try:
            start(next(item_iter))
        except StopIteration:
            pass

    print(f"\n{done} pass(es) done, {skipped} skipped, {time.time() - t0:.0f}s total")
    print("now run:  python scripts/summarise_runs.py --glob 'output/full/*.json' --out output/FULL_DATASET.md")
    print("          python scripts/variant_agreement.py --output-dir output/full --out output/FULL_VARIANT_AGREEMENT.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
