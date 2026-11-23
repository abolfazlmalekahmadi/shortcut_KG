"""Run-based (no-rasterisation) computation of the same measures.

``measures.measure_masks`` rasterises the three masks and then works on pixel arrays.
On ``OriginalResolution`` grids (up to ~3000x3000) that costs ~0.3 s per image, which is
fine for 200 rows and hopeless for 657k. This module gets the identical numbers straight
from the run list:

* every run is a contiguous stretch of set pixels in the row-major raster, so a run
  contributes to **one row** if it does not reach the right edge, and to **two rows**
  (the tail of one, the head of the next) if it does; a row fully inside a run is
  entirely set;
* a CheXmask organ is a single filled contour, so each row of one organ is a single
  interval. That makes area, bounding box, per-row extents, centroid and even the union
  of the two lungs computable from a few thousand intervals, in arrays of length
  ``height`` instead of ``height * width``.

``tests/test_fast_engine.py`` checks every measure against the raster path on real rows
from all five datasets; the two must agree exactly (centroid within float tolerance).
"""

from __future__ import annotations

import numpy as np

from .measures import MASK_COLUMNS  # noqa: F401  (re-exported for callers)

__all__ = ["measure_rle", "run_extents", "row_extents_from_runs", "parse_runs"]


def parse_runs(rle: str) -> tuple[np.ndarray, np.ndarray]:
    """``"start length start length ..."`` -> ``(starts_0based, lengths)``."""
    if not rle or not rle.strip():
        empty = np.empty(0, dtype=np.int64)
        return empty, empty
    try:
        values = np.fromstring(rle, dtype=np.int64, sep=" ")
    except Exception:  # pragma: no cover - depends on numpy version
        values = np.array(rle.split(), dtype=np.int64)
    starts = values[0::2] - 1
    lengths = values[1::2]
    keep = (lengths > 0) & (starts >= 0)
    return starts[keep], lengths[keep]


def run_extents(starts: np.ndarray, lengths: np.ndarray, width: int) -> tuple[np.ndarray, ...]:
    """Decompose runs into ``(y0, x0, y1, x1)`` with ``[x0, x1]`` inclusive.

    ``y0 == y1`` for a run that stays inside one row; otherwise the run leaves row ``y0``
    at column ``width - 1`` and enters row ``y1`` at column 0.
    """
    y0 = starts // width
    x0 = starts - y0 * width
    last = starts + lengths - 1
    y1 = last // width
    x1 = last - y1 * width
    return y0, x0, y1, x1


def row_extents_from_runs(
    starts: np.ndarray, lengths: np.ndarray, height: int, width: int
) -> tuple[np.ndarray, np.ndarray]:
    """Per-row ``(min_x, max_x)`` inclusive; ``min_x == width`` marks an empty row."""
    min_x = np.full(height, width, dtype=np.int64)
    max_x = np.full(height, -1, dtype=np.int64)
    if starts.size == 0:
        return min_x, max_x

    y0, x0, y1, x1 = run_extents(starts, lengths, width)
    single = y0 == y1
    if single.any():
        np.minimum.at(min_x, y0[single], x0[single])
        np.maximum.at(max_x, y0[single], x1[single])

    multi = ~single
    if multi.any():
        a, b, c, d = y0[multi], x0[multi], y1[multi], x1[multi]
        np.minimum.at(min_x, a, b)
        np.maximum.at(max_x, a, width - 1)
        np.minimum.at(min_x, c, 0)
        np.maximum.at(max_x, c, d)
        # rows strictly inside a run are completely set (rare: needs a full row)
        spanning = (c - a) > 1
        for lo, hi in zip(a[spanning] + 1, c[spanning]):
            min_x[lo:hi] = 0
            max_x[lo:hi] = width - 1
    return min_x, max_x


def _row_columns(starts: np.ndarray, lengths: np.ndarray, height: int, width: int):
    """``(rows, first_x, last_x)`` for the rows a mask occupies."""
    min_x, max_x = row_extents_from_runs(starts, lengths, height, width)
    rows = np.nonzero(min_x < width)[0]
    return rows, min_x[rows], max_x[rows]


def _align(rows: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Index of each ``target`` row inside ``rows`` (clipped) and whether it is there."""
    if rows.size == 0:
        return np.zeros(target.size, dtype=np.int64), np.zeros(target.size, dtype=bool)
    pos = np.searchsorted(rows, target)
    pos_clipped = np.minimum(pos, rows.size - 1)
    return pos_clipped, (pos < rows.size) & (rows[pos_clipped] == target)


def _sums(starts: np.ndarray, lengths: np.ndarray, width: int) -> tuple[int, int]:
    """Exact ``sum(x)`` and ``sum(y)`` over the set pixels (integer arithmetic)."""
    if starts.size == 0:
        return 0, 0
    y0, x0, y1, x1 = run_extents(starts, lengths, width)
    single = y0 == y1

    x_sum = y_sum = 0
    if single.any():
        a, b, c = x0[single], x1[single], y0[single]
        counts = b - a + 1
        x_sum += int(((a + b) * counts // 2).sum())
        y_sum += int((c * counts).sum())

    multi = ~single
    if multi.any():
        a, b, c, d = y0[multi], x0[multi], y1[multi], x1[multi]
        # first row: x from b to width-1
        n1 = width - b
        x_sum += int(((b + width - 1) * n1 // 2).sum())
        y_sum += int((a * n1).sum())
        # last row: x from 0 to d
        n2 = d + 1
        x_sum += int(((0 + d) * n2 // 2).sum())
        y_sum += int((c * n2).sum())
        # full rows between them
        gap = c - a - 1
        if (gap > 0).any():
            full_x = width * (width - 1) // 2
            x_sum += int((gap[gap > 0].sum()) * full_x)
            for lo, hi in zip(a[gap > 0] + 1, c[gap > 0]):
                y_sum += int(np.arange(lo, hi).sum()) * width
    return x_sum, y_sum


def _intervals_in_row(
    starts: np.ndarray, lengths: np.ndarray, width: int, y: int
) -> list[tuple[int, int]]:
    """The ``[lo, hi]`` intervals of set pixels in row ``y`` of one mask."""
    if starts.size == 0:
        return []
    y0, x0, y1, x1 = run_extents(starts, lengths, width)
    out = []
    for i in np.nonzero((y0 <= y) & (y1 >= y))[0]:
        if y0[i] == y1[i]:
            out.append((int(x0[i]), int(x1[i])))
        elif y == y0[i]:
            out.append((int(x0[i]), width - 1))
        elif y == y1[i]:
            out.append((0, int(x1[i])))
        else:
            out.append((0, width - 1))
    return out


def _exact_overlap_in_row(
    left: tuple[np.ndarray, np.ndarray],
    right: tuple[np.ndarray, np.ndarray],
    width: int,
    y: int,
) -> int:
    """``|left ∩ right|`` in row ``y``, exactly, from the intervals of both masks."""
    total = 0
    for lo_l, hi_l in _intervals_in_row(*left, width, y):
        for lo_r, hi_r in _intervals_in_row(*right, width, y):
            total += max(0, min(hi_l, hi_r) - max(lo_l, lo_r) + 1)
    return total


def _max_row_width(first_x: np.ndarray, last_x: np.ndarray, width: int) -> tuple[int, int]:
    if first_x.size == 0:
        return 0, -1
    widths = last_x - first_x + 1
    i = int(np.argmax(widths))
    return int(widths[i]), i  # index into the compacted rows array


def measure_rle(
    heart_rle: str,
    left_lung_rle: str,
    right_lung_rle: str,
    height: int,
    width: int,
    *,
    prefix: str = "",
) -> dict:
    """Same keys and values as :func:`chexmask_anatomy.measures.measure_masks`.

    ``height`` and ``width`` must be the ``Height``/``Width`` columns of the same row.
    """
    heart = parse_runs(heart_rle)
    left = parse_runs(left_lung_rle)
    right = parse_runs(right_lung_rle)

    h_area, l_area, r_area = (int(p[1].sum()) for p in (heart, left, right))
    image_area = float(height * width)

    h_rows, h_fx, h_lx = _row_columns(*heart, height, width)
    l_rows, l_fx, l_lx = _row_columns(*left, height, width)
    r_rows, r_fx, r_lx = _row_columns(*right, height, width)

    # ---- union of the two lungs -------------------------------------------------
    # Each lung is a single interval per row, so the union of one row is the pair of
    # those two intervals. Vectorised: align both organs on the union of their rows.
    u_rows = np.union1d(l_rows, r_rows)
    if u_rows.size:
        li, has_l = _align(l_rows, u_rows)
        ri, has_r = _align(r_rows, u_rows)
        both = has_l & has_r
        u_fx = np.where(both, np.minimum(l_fx[li], r_fx[ri]),
                        np.where(has_l, l_fx[li], r_fx[ri]))
        u_lx = np.where(both, np.maximum(l_lx[li], r_lx[ri]),
                        np.where(has_l, l_lx[li], r_lx[ri]))
        # The two intervals are an upper bound on the true overlap: a row of an organ can
        # hold more than one interval (gaps), and then the bounding pair is wider than the
        # pixels. When the bound is non-zero, redo those rows exactly. Rare enough to keep
        # the loop (and ``tests/test_fast_engine.py`` checks the result anyway).
        bound = np.zeros(u_rows.size, dtype=np.int64)
        bound[both] = np.maximum(
            0,
            np.minimum(l_lx[li[both]], r_lx[ri[both]])
            - np.maximum(l_fx[li[both]], r_fx[ri[both]])
            + 1,
        )
        exact = np.nonzero(bound > 0)[0]
        if exact.size == 0:
            overlap = 0
        else:
            overlap = sum(
                _exact_overlap_in_row(left, right, width, int(u_rows[k])) for k in exact
            )
    else:
        u_fx = np.empty(0, dtype=np.int64)
        u_lx = np.empty(0, dtype=np.int64)
        overlap = 0
    u_area = l_area + r_area - overlap

    out: dict = {}

    # ---- areas -----------------------------------------------------------------
    out["heart_area_px"] = h_area
    out["left_lung_area_px"] = l_area
    out["right_lung_area_px"] = r_area
    out["lung_area_px"] = u_area
    out["heart_area_frac"] = h_area / image_area
    out["left_lung_area_frac"] = l_area / image_area
    out["right_lung_area_frac"] = r_area / image_area
    out["lung_area_frac"] = u_area / image_area
    out["heart_lung_area_ratio"] = h_area / u_area if u_area else float("nan")

    # ---- widths and heights ----------------------------------------------------
    heart_width, _ = _max_row_width(h_fx, h_lx, width)
    thorax_width, _ = _max_row_width(u_fx, u_lx, width)
    out["heart_width_px"] = heart_width
    out["thorax_width_px"] = thorax_width
    out["heart_width_norm"] = heart_width / width if width else float("nan")
    out["thorax_width_norm"] = thorax_width / width if width else float("nan")
    out["left_lung_width_px"] = _max_row_width(l_fx, l_lx, width)[0]
    out["right_lung_width_px"] = _max_row_width(r_fx, r_lx, width)[0]
    out["lung_width_asymmetry"] = (
        (l_area - r_area) / (l_area + r_area) if (l_area + r_area) else float("nan")
    )

    if h_rows.size:
        heart_bbox = (
            int(h_rows[0]),
            int(h_fx.min()),
            int(h_rows[-1]),
            int(h_lx.max()),
        )
    else:
        heart_bbox = (-1, -1, -1, -1)
    if u_rows.size:
        lung_bbox = (int(u_rows[0]), int(u_fx.min()), int(u_rows[-1]), int(u_lx.max()))
    else:
        lung_bbox = (-1, -1, -1, -1)

    hy0, hx0, hy1, hx1 = heart_bbox
    ly0, lx0, ly1, lx1 = lung_bbox
    out["heart_bbox_width_px"] = hx1 - hx0 + 1 if hx0 >= 0 else 0
    out["heart_bbox_height_px"] = hy1 - hy0 + 1 if hy0 >= 0 else 0
    out["lung_bbox_width_px"] = lx1 - lx0 + 1 if lx0 >= 0 else 0
    out["lung_bbox_height_px"] = ly1 - ly0 + 1 if ly0 >= 0 else 0

    # ---- cardiothoracic ratio --------------------------------------------------
    out["ctr"] = heart_width / thorax_width if thorax_width else float("nan")
    heart_row = int(h_rows[int(np.argmax(h_lx - h_fx))]) if h_rows.size else -1
    if heart_row >= 0:
        match = np.nonzero(u_rows == heart_row)[0]
        same_row_width = int(u_lx[match[0]] - u_fx[match[0]] + 1) if match.size else 0
        out["ctr_same_level"] = heart_width / same_row_width if same_row_width else float("nan")
    else:
        out["ctr_same_level"] = float("nan")
    out["ctr_bbox"] = (
        out["heart_bbox_width_px"] / out["lung_bbox_width_px"]
        if out["lung_bbox_width_px"]
        else float("nan")
    )

    # ---- position --------------------------------------------------------------
    hx_sum, hy_sum = _sums(*heart, width)
    ux_sum, uy_sum = _sums(*left, width)
    ux2_sum, uy2_sum = _sums(*right, width)
    ux_sum += ux2_sum
    uy_sum += uy2_sum

    def _centroid(x_sum, y_sum, area):
        if not area:
            return float("nan"), float("nan")
        return (x_sum / area) / width, (y_sum / area) / height

    hcx, hcy = _centroid(hx_sum, hy_sum, h_area)
    lcx, lcy = _centroid(ux_sum, uy_sum, u_area)
    out["heart_centroid_x_norm"] = hcx
    out["heart_centroid_y_norm"] = hcy
    out["lung_centroid_x_norm"] = lcx
    out["lung_centroid_y_norm"] = lcy

    for name, box in (("heart", heart_bbox), ("lung", lung_bbox)):
        y0, x0, y1, x1 = box
        if x0 < 0:
            for side in ("left", "top", "right", "bottom"):
                out[f"{name}_bbox_{side}_norm"] = float("nan")
        else:
            out[f"{name}_bbox_left_norm"] = x0 / width
            out[f"{name}_bbox_top_norm"] = y0 / height
            out[f"{name}_bbox_right_norm"] = (width - 1 - x1) / width
            out[f"{name}_bbox_bottom_norm"] = (height - 1 - y1) / height

    out["lung_touches_border"] = bool(
        u_rows.size
        and (
            u_rows[0] == 0
            or u_rows[-1] == height - 1
            or u_fx.min() == 0
            or u_lx.max() == width - 1
        )
    )

    if prefix:
        out = {f"{prefix}{k}": v for k, v in out.items()}
    return out
