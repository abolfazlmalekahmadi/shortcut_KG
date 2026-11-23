"""The run-based engine must return exactly what the raster engine returns.

The raster engine (``measures.measure_masks``) is the reference: it is short, it is
checked against a naive row-by-row loop in ``test_checks.py``, and its masks are checked
against the authors' published decoder. The fast engine (``measures_rle.measure_rle``)
skips rasterisation, so it needs its own evidence — this file.

Run directly (``python tests/test_fast_engine.py``) or with pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chexmask_anatomy import decode_rle, measure_masks, read_selected_records, resolve_paths  # noqa: E402
from chexmask_anatomy.measures_rle import measure_rle, row_extents_from_runs, parse_runs  # noqa: E402

DATASETS = ["vindr", "chexpert", "mimic", "padchest", "chestxray8"]
DATA_ROOT = REPO_ROOT / "data"

# Rows per dataset/variant. OriginalResolution masks are ~10x the pixels of the
# preprocessed ones, so the reference path is what limits how many we can afford.
N = {"original": 25, "preprocessed": 60}


def _compare(measures_fast: dict, measures_ref: dict, where: str) -> None:
    assert set(measures_fast) == set(measures_ref), (
        f"{where}: key mismatch "
        f"{set(measures_fast) ^ set(measures_ref)}"
    )
    for key, ref in measures_ref.items():
        got = measures_fast[key]
        if isinstance(ref, bool) or isinstance(ref, int):
            assert got == ref, f"{where}: {key}: {got!r} != {ref!r}"
        elif isinstance(ref, float) and isinstance(got, float) and np.isnan(ref) and np.isnan(got):
            continue
        else:
            assert np.isclose(got, ref, rtol=1e-9, atol=1e-12), (
                f"{where}: {key}: {got!r} != {ref!r}"
            )


def _rows(dataset: str, variant: str):
    spec, path = resolve_paths(dataset, variant, DATA_ROOT)
    header, records = read_selected_records(path, N[variant], sample="random", seed=1234, scan=4000)
    return spec, header, records


def test_fast_matches_raster() -> None:
    checked = 0
    for dataset in DATASETS:
        for variant in ("original", "preprocessed"):
            if getattr(__import__("chexmask_anatomy").DATASETS[dataset], variant) is None:
                continue
            spec, header, records = _rows(dataset, variant)
            for record in records:
                row = dict(zip(header, record))
                h, w = int(row["Height"]), int(row["Width"])
                masks = {k: decode_rle(row[k], h, w) > 0 for k in ("Heart", "Left Lung", "Right Lung")}
                ref = measure_masks(masks["Heart"], masks["Left Lung"], masks["Right Lung"])
                fast = measure_rle(row["Heart"], row["Left Lung"], row["Right Lung"], h, w)
                _compare(fast, ref, f"{dataset}/{variant}/{row[spec.id_column][:24]}")
                checked += 1
    print(f"  compared {checked} images across {len(DATASETS)} datasets")
    assert checked >= 100


def test_area_equals_sum_of_run_lengths() -> None:
    """Runs are disjoint and exact, so lengths sum to the raster area."""
    for dataset in ("vindr", "padchest"):
        spec, header, records = _rows(dataset, "preprocessed")
        for record in records[:20]:
            row = dict(zip(header, record))
            h, w = int(row["Height"]), int(row["Width"])
            for name in ("Heart", "Left Lung", "Right Lung"):
                starts, lengths = parse_runs(row[name])
                raster = int((decode_rle(row[name], h, w) > 0).sum())
                assert int(lengths.sum()) == raster, f"{dataset} {name}: {lengths.sum()} != {raster}"


def test_row_extents_match_raster_even_with_gaps() -> None:
    """Per-row (min_x, max_x) must equal the raster's, whatever the row looks like.

    This also documents that a row of an organ is **not** always one contiguous
    interval: the sample below finds such rows, and they are why the union overlap is
    re-checked exactly instead of being taken from the bounding intervals.
    """
    gapped_rows = 0
    for dataset in ("vindr", "chexpert", "padchest"):
        spec, header, records = _rows(dataset, "preprocessed")
        for record in records[:10]:
            row = dict(zip(header, record))
            h, w = int(row["Height"]), int(row["Width"])
            for name in ("Heart", "Left Lung", "Right Lung"):
                starts, lengths = parse_runs(row[name])
                min_x, max_x = row_extents_from_runs(starts, lengths, h, w)
                mask = decode_rle(row[name], h, w) > 0
                occupied = mask.any(axis=1)
                assert np.array_equal(occupied, min_x < w), f"{dataset} {name}: occupancy"
                rows = np.nonzero(occupied)[0]
                if rows.size == 0:
                    continue
                sub = mask[rows]
                first = np.argmax(sub, axis=1)
                last = sub.shape[1] - 1 - np.argmax(sub[:, ::-1], axis=1)
                assert np.array_equal(min_x[rows], first), f"{dataset} {name}: min_x"
                assert np.array_equal(max_x[rows], last), f"{dataset} {name}: max_x"
                gapped_rows += int((sub.sum(axis=1) != last - first + 1).sum())
    print(f"  found {gapped_rows} rows holding more than one interval")
    assert gapped_rows > 0, "the sample should contain non-contiguous rows"


def test_multi_interval_rows_are_handled_exactly() -> None:
    """Images whose masks have gapped rows must still match the raster engine exactly."""
    checked = 0
    for dataset in ("vindr", "padchest"):
        spec, header, records = _rows(dataset, "preprocessed")
        for record in records[:40]:
            row = dict(zip(header, record))
            h, w = int(row["Height"]), int(row["Width"])
            masks = {k: decode_rle(row[k], h, w) > 0 for k in ("Heart", "Left Lung", "Right Lung")}
            gapped = False
            for mask in masks.values():
                sub = mask[mask.any(axis=1)]
                if sub.size:
                    first = np.argmax(sub, axis=1)
                    last = sub.shape[1] - 1 - np.argmax(sub[:, ::-1], axis=1)
                    gapped |= bool((sub.sum(axis=1) != last - first + 1).any())
            if not gapped:
                continue
            ref = measure_masks(masks["Heart"], masks["Left Lung"], masks["Right Lung"])
            fast = measure_rle(row["Heart"], row["Left Lung"], row["Right Lung"], h, w)
            _compare(fast, ref, f"gapped {dataset}/{row[spec.id_column][:24]}")
            checked += 1
    print(f"  compared {checked} images that contain gapped rows")
    assert checked >= 3


def test_empty_organ_is_handled() -> None:
    """An empty mask must not break either engine, and they must still agree.

    Not hypothetical: at least one PadChest row ships an empty organ (that is how the
    first full-dataset run failed).
    """
    spec, header, records = _rows("padchest", "preprocessed")
    organs = ("Heart", "Left Lung", "Right Lung")
    checked = 0
    for record in records[:8]:
        row = dict(zip(header, record))
        h, w = int(row["Height"]), int(row["Width"])
        for blank in organs:
            rles = {k: ("" if k == blank else row[k]) for k in organs}
            ref = measure_masks(*[decode_rle(rles[k], h, w) > 0 for k in organs])
            fast = measure_rle(rles["Heart"], rles["Left Lung"], rles["Right Lung"], h, w)
            _compare(fast, ref, f"{spec.key}: blank {blank}")
            checked += 1
        for blank in (("Left Lung", "Right Lung"), organs):
            rles = {k: ("" if k in blank else row[k]) for k in organs}
            ref = measure_masks(*[decode_rle(rles[k], h, w) > 0 for k in organs])
            fast = measure_rle(rles["Heart"], rles["Left Lung"], rles["Right Lung"], h, w)
            _compare(fast, ref, f"{spec.key}: blank {blank}")
            checked += 1
    print(f"  compared {checked} synthetic empty-organ cases")
    assert checked >= 40


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    raise SystemExit(1 if failures else 0)
