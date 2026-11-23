"""Reading CheXmask CSVs.

The CSVs are large (0.3-13 GB) and every row carries three multi-kilobyte RLE strings,
so nothing here loads a whole file. Records are read with the stdlib ``csv`` module,
which — unlike ``pandas.skiprows`` — understands that the ``Landmarks`` field contains
embedded newlines inside a quoted field. Physical line numbers therefore cannot be used
to select rows; record indices can.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

__all__ = ["DATASETS", "DatasetSpec", "resolve_paths", "read_selected_records", "parse_landmarks"]


@dataclass(frozen=True)
class DatasetSpec:
    """One source dataset, as shipped in the CheXmask release."""

    key: str
    label: str
    id_column: str
    original: str | None
    preprocessed: str | None
    n_images: int | None = None  # filled in when known


#: The five chest X-ray datasets CheXmask covers. ``original``/``preprocessed`` are the
#: file names inside ``data/OriginalResolution`` and ``data/Preprocessed``.
DATASETS: dict[str, DatasetSpec] = {
    "vindr": DatasetSpec("vindr", "VinDr-CXR", "image_id", "VinDr-CXR.csv", "VinDr-CXR.csv"),
    "chexpert": DatasetSpec("chexpert", "CheXpert", "Path", "CheXpert.csv", "CheXpert.csv"),
    "mimic": DatasetSpec("mimic", "MIMIC-CXR-JPG", "dicom_id", "MIMIC-CXR-JPG.csv", "MIMIC-CXR-JPG.csv"),
    "padchest": DatasetSpec("padchest", "PadChest", "ImageID", "Padchest.csv", "Padchest.csv"),
    "chestxray8": DatasetSpec(
        "chestxray8", "ChestX-Ray8", "Image Index", "ChestX-Ray8.csv", None
    ),
}


def resolve_paths(dataset: str, variant: str, data_root: Path) -> tuple[DatasetSpec, Path]:
    """Map ``--dataset``/``--variant`` onto a concrete CSV path."""
    if dataset not in DATASETS:
        raise KeyError(f"unknown dataset {dataset!r}; known: {sorted(DATASETS)}")
    spec = DATASETS[dataset]
    fname = getattr(spec, variant)
    if fname is None:
        raise ValueError(
            f"{spec.label} has no '{variant}' variant in the CheXmask release "
            f"(available: {[v for v in ('original', 'preprocessed') if getattr(spec, v)]})"
        )
    subdir = {"original": "OriginalResolution", "preprocessed": "Preprocessed"}[variant]
    path = Path(data_root) / subdir / fname
    if not path.exists():
        raise FileNotFoundError(path)
    return spec, path


def open_records(
    path: Path,
    n: int | None = None,
    *,
    sample: str = "first",
    seed: int = 0,
    scan: int = 50_000,
):
    """Stream records from ``path`` without holding them all in memory.

    Returns ``(header, iterator)``. ``n=None`` reads every record; ``sample="random"``
    draws ``n`` records from the first ``scan`` with ``seed``, which keeps sampling a
    13 GB file bounded.

    The iterator must be consumed (or closed) before the file handle is released; it
    closes itself when exhausted or garbage-collected.
    """
    fh = open(path, newline="", encoding="utf-8", errors="replace")
    reader = csv.reader(fh)
    header = next(reader)

    if n is not None and n <= 0:
        fh.close()
        raise ValueError("n must be positive or None")

    wanted: set[int] | None = None
    last_wanted: int | None = None
    if sample == "random":
        if n is None:
            raise ValueError("sample='random' needs an n")
        if scan < n:
            fh.close()
            raise ValueError(f"--scan ({scan}) must be >= --n ({n})")
        wanted = set(np.random.default_rng(seed).choice(scan, size=n, replace=False).tolist())
        last_wanted = max(wanted)
    elif sample != "first":
        fh.close()
        raise ValueError("sample must be 'first' or 'random'")

    def iterator():
        try:
            count = 0
            for i, record in enumerate(reader):
                if wanted is None or i in wanted:
                    yield record
                    count += 1
                    if n is not None and count >= n:
                        break
                if last_wanted is not None and i >= last_wanted:
                    break
            if n is not None and count < n:
                print(f"  note: only {count} records available (asked for {n})", file=sys.stderr)
        finally:
            fh.close()

    return header, iterator()


def read_selected_records(
    path: Path,
    n: int,
    *,
    sample: str = "first",
    seed: int = 0,
    scan: int = 50_000,
) -> tuple[list[str], list[list[str]]]:
    """Materialise ``n`` records (convenience wrapper over :func:`open_records`)."""
    header, records = open_records(path, n, sample=sample, seed=seed, scan=scan)
    return header, list(records)


def parse_landmarks(cell: str) -> np.ndarray:
    """Parse the ``Landmarks`` cell into an ``(N, 2)`` int array of ``[x, y]``.

    The cell holds a numpy-style array dump with newlines, e.g.
    ``"[[ 831  242]\\n [ 734  261]\\n ...]"``. Landmark groups are concatenated in the
    order right lung (44 points), left lung (50), heart (count varies).
    """
    if not cell:
        return np.empty((0, 2), dtype=np.int32)
    text = cell.replace("[", " ").replace("]", " ").replace("\n", " ").replace(",", " ")
    values = np.array(text.split(), dtype=np.int32)
    return values.reshape(-1, 2)
