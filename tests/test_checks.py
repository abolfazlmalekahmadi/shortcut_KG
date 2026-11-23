"""Checks for the RLE codec and the measures.

Run directly (``python tests/test_checks.py``) or with pytest. The data-backed checks are
skipped when ``data/OriginalResolution/VinDr-CXR.csv`` is absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from chexmask_anatomy import (  # noqa: E402
    MASK_COLUMNS,
    decode_rle,
    decode_rle_ref,
    encode_rle,
    measure_masks,
    parse_landmarks,
    read_selected_records,
)

DATA = REPO_ROOT / "data" / "OriginalResolution" / "VinDr-CXR.csv"


def test_roundtrip_random_masks() -> None:
    rng = np.random.default_rng(0)
    for _ in range(20):
        h, w = rng.integers(1, 40, size=2)
        mask = rng.random((h, w)) < rng.uniform(0.05, 0.6)
        rle = encode_rle(mask)
        assert np.array_equal(decode_rle(rle, h, w) > 0, mask)
        assert np.array_equal(decode_rle_ref(rle, h, w) > 0, mask)


def test_empty_mask() -> None:
    assert decode_rle("", 7, 5).sum() == 0
    assert decode_rle_ref("", 7, 5).sum() == 0


def test_fast_matches_reference_on_real_rows() -> None:
    if not DATA.exists():
        print("skip: no data")
        return
    header, records = read_selected_records(DATA, 25)
    for record in records:
        row = dict(zip(header, record))
        h, w = int(row["Height"]), int(row["Width"])
        for name in MASK_COLUMNS:
            fast = decode_rle(row[name], h, w)
            ref = decode_rle_ref(row[name], h, w)
            assert np.array_equal(fast, ref), f"mismatch on {name} of {row['image_id']}"


def test_measures_sanity_on_real_rows() -> None:
    if not DATA.exists():
        print("skip: no data")
        return
    header, records = read_selected_records(DATA, 15)
    for record in records:
        row = dict(zip(header, record))
        h, w = int(row["Height"]), int(row["Width"])
        me = measure_masks(
            decode_rle(row["Heart"], h, w) > 0,
            decode_rle(row["Left Lung"], h, w) > 0,
            decode_rle(row["Right Lung"], h, w) > 0,
        )
        for k in ("heart_area_px", "left_lung_area_px", "right_lung_area_px", "lung_area_px"):
            assert 0 < me[k] < h * w, f"{k} out of range for {row['image_id']}"
        assert 0.0 < me["ctr"] < 1.5
        assert me["heart_width_px"] <= me["thorax_width_px"] * 1.2
        assert 0.05 < me["lung_area_frac"] < 0.85
        assert abs(me["lung_area_px"] - (me["left_lung_area_px"] + me["right_lung_area_px"])) / me[
            "lung_area_px"
        ] < 0.35, "lung union should be close to the sum of the two lungs"


def test_measures_match_naive_reference() -> None:
    """The vectorised helpers must agree with an obvious row-by-row computation."""
    if not DATA.exists():
        print("skip: no data")
        return

    def naive_max_row_width(mask: np.ndarray) -> int:
        widths = []
        for y in range(mask.shape[0]):
            xs = np.nonzero(mask[y])[0]
            if xs.size:
                widths.append(int(xs.max() - xs.min() + 1))
        return max(widths) if widths else 0

    header, records = read_selected_records(DATA, 5)
    for record in records:
        row = dict(zip(header, record))
        h, w = int(row["Height"]), int(row["Width"])
        heart = decode_rle(row["Heart"], h, w) > 0
        left = decode_rle(row["Left Lung"], h, w) > 0
        right = decode_rle(row["Right Lung"], h, w) > 0
        me = measure_masks(heart, left, right)

        union = left | right
        assert me["heart_width_px"] == naive_max_row_width(heart), row["image_id"]
        assert me["thorax_width_px"] == naive_max_row_width(union), row["image_id"]
        assert me["heart_area_px"] == int(heart.sum())
        assert me["left_lung_area_px"] == int(left.sum())
        assert me["right_lung_area_px"] == int(right.sum())
        assert me["lung_area_px"] == int(union.sum())
        assert me["ctr"] == me["heart_width_px"] / me["thorax_width_px"]
        ys, xs = np.nonzero(union)
        assert me["lung_bbox_width_px"] == int(xs.max() - xs.min() + 1)


def test_landmarks_parse() -> None:
    if not DATA.exists():
        print("skip: no data")
        return
    header, records = read_selected_records(DATA, 1)
    row = dict(zip(header, records[0]))
    lm = parse_landmarks(row["Landmarks"])
    assert lm.shape[1] == 2
    assert lm.shape[0] >= 94  # 44 right lung + 50 left lung + heart
    h, w = int(row["Height"]), int(row["Width"])
    assert lm[:, 0].max() <= w and lm[:, 1].max() <= h


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
    raise SystemExit(1 if failures else 0)
