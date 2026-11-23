"""Per-image anatomical measures derived from CheXmask segmentation masks.

Scope: the first step of E1 in the project brief — turn the heart / left-lung /
right-lung masks of one image into a small set of numbers that can later be joined into
a per-image knowledge graph and tested for shortcut signal.

Definitions used here
---------------------
All widths are measured on the *mask*, in pixels of that image's own grid.

``heart_width_px``
    Maximal transverse cardiac diameter: the widest horizontal extent of the heart mask,
    ``max_y (max_x - min_x + 1)`` over the rows the heart occupies.

``thorax_width_px``
    Maximal inner thoracic diameter, approximated by the widest horizontal extent of the
    *lung union* (both lungs together), ``max_y (max_x - min_x + 1)``.

``ctr``
    Cardiothoracic ratio = ``heart_width_px / thorax_width_px``. Two alternative
    definitions are also reported because the literature is not unanimous:

    * ``ctr_same_level`` — heart width at the row where the heart is widest, divided by
      the thorax width at that *same* row;
    * ``ctr_bbox`` — heart bounding-box width / lung-union bounding-box width.

Two families of measure behave differently between the two released variants
(``OriginalResolution`` and ``Preprocessed``), and the distinction matters:

* **mask-against-mask ratios** — ``ctr``, ``ctr_same_level``, ``ctr_bbox``,
  ``heart_lung_area_ratio``, ``lung_width_asymmetry`` — depend only on the masks, so an
  isotropic resampling cancels out. ``scripts/compare_variants.py`` measures the
  agreement on 200 VinDr-CXR images and it is better than 0.2% for CTR.
* **frame-normalised measures** — ``*_area_frac``, ``*_width_norm``, ``*_centroid_*_norm``,
  ``*_bbox_*_norm`` and ``image_aspect`` — divide by the image frame. ``Preprocessed``
  pads each image to a square *before* resizing to 1024x1024, so the frame is not the
  frame of the original acquisition and these measures shift by ~13% on average. They
  are only comparable within one variant, and only ``OriginalResolution`` keeps the
  original frame.

Use ``OriginalResolution`` when the question involves where things sit in the image
(positioning, cropping, collimation — the E1 shortcut candidates). Either variant is
fine for CTR.

The masks say nothing about physical size: CheXmask ships no pixel spacing. So areas are
kept as pixels and as a fraction of the image, never as mm².
"""

from __future__ import annotations

import numpy as np

__all__ = ["MASK_COLUMNS", "measure_masks", "row_extent_profile"]

# Column names as they appear in every CheXmask CSV.
MASK_COLUMNS = ("Heart", "Left Lung", "Right Lung")


def row_extent_profile(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row horizontal extent of a boolean mask.

    Returns ``(first, last)`` arrays over the image rows, with ``-1`` where the row is
    empty.
    """
    h, w = mask.shape
    first = np.full(h, -1, dtype=np.int32)
    last = np.full(h, -1, dtype=np.int32)
    if w == 0:
        return first, last
    nonempty = mask.any(axis=1)
    if not nonempty.any():
        return first, last
    rows = np.nonzero(nonempty)[0]
    sub = mask[rows]
    first[rows] = np.argmax(sub, axis=1)
    last[rows] = w - 1 - np.argmax(sub[:, ::-1], axis=1)
    return first, last


def _max_row_width(mask: np.ndarray) -> tuple[int, int]:
    """Widest horizontal extent of a mask and the row where it occurs.

    Returns ``(width_px, row)``; ``(0, -1)`` for an empty mask.
    """
    first, last = row_extent_profile(mask)
    widths = np.where(first >= 0, last - first + 1, 0)
    if not widths.any():
        return 0, -1
    row = int(np.argmax(widths))
    return int(widths[row]), row


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    """Bounding box ``(y0, x0, y1, x1)`` inclusive; ``(-1, -1, -1, -1)`` if empty."""
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return -1, -1, -1, -1
    return int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())


def _centroid(mask: np.ndarray) -> tuple[float, float]:
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return float("nan"), float("nan")
    return float(xs.mean()), float(ys.mean())


def measure_masks(
    heart: np.ndarray,
    left_lung: np.ndarray,
    right_lung: np.ndarray,
    *,
    prefix: str = "",
) -> dict:
    """Compute the anatomical measures for one image.

    Parameters
    ----------
    heart, left_lung, right_lung
        Boolean (or 0/255) masks of identical shape. Low-quality segmentations are the
        caller's problem: filter on ``Dice RCA (Mean)`` before trusting the numbers.
    prefix
        Prepended to every key, e.g. ``"heart_"``; useful when a caller computes more
        than one set of measures per row.

    Returns
    -------
    dict
        Measure name -> value. Empty masks give 0 areas and ``nan`` for ratios.
    """
    heart = np.asarray(heart) > 0
    left_lung = np.asarray(left_lung) > 0
    right_lung = np.asarray(right_lung) > 0
    if not (heart.shape == left_lung.shape == right_lung.shape):
        raise ValueError("heart, left and right lung masks must share a shape")

    h, w = heart.shape
    image_area = float(h * w)
    lung_union = left_lung | right_lung

    out: dict = {}

    # ---- areas -----------------------------------------------------------------
    heart_area = int(heart.sum())
    left_area = int(left_lung.sum())
    right_area = int(right_lung.sum())
    union_area = int(lung_union.sum())
    out["heart_area_px"] = heart_area
    out["left_lung_area_px"] = left_area
    out["right_lung_area_px"] = right_area
    out["lung_area_px"] = union_area
    out["heart_area_frac"] = heart_area / image_area
    out["left_lung_area_frac"] = left_area / image_area
    out["right_lung_area_frac"] = right_area / image_area
    out["lung_area_frac"] = union_area / image_area
    out["heart_lung_area_ratio"] = heart_area / union_area if union_area else float("nan")

    # ---- widths and heights ----------------------------------------------------
    heart_width, heart_row = _max_row_width(heart)
    thorax_width, _ = _max_row_width(lung_union)
    out["heart_width_px"] = heart_width
    out["thorax_width_px"] = thorax_width
    out["heart_width_norm"] = heart_width / w if w else float("nan")
    out["thorax_width_norm"] = thorax_width / w if w else float("nan")

    # per-lung transverse extents, for asymmetry
    for name, m in (("left", left_lung), ("right", right_lung)):
        width_px, _ = _max_row_width(m)
        out[f"{name}_lung_width_px"] = width_px
    out["lung_width_asymmetry"] = (
        (left_area - right_area) / (left_area + right_area)
        if (left_area + right_area)
        else float("nan")
    )

    hy0, hx0, hy1, hx1 = _bbox(heart)
    ly0, lx0, ly1, lx1 = _bbox(lung_union)
    out["heart_bbox_width_px"] = hx1 - hx0 + 1 if hx0 >= 0 else 0
    out["heart_bbox_height_px"] = hy1 - hy0 + 1 if hy0 >= 0 else 0
    out["lung_bbox_width_px"] = lx1 - lx0 + 1 if lx0 >= 0 else 0
    out["lung_bbox_height_px"] = ly1 - ly0 + 1 if ly0 >= 0 else 0

    # ---- cardiothoracic ratio --------------------------------------------------
    out["ctr"] = heart_width / thorax_width if thorax_width else float("nan")
    if heart_row >= 0:
        # Thoracic width measured at the same row as the widest cardiac diameter.
        t_first, t_last = row_extent_profile(lung_union)
        same_row_width = (
            int(t_last[heart_row] - t_first[heart_row] + 1) if t_first[heart_row] >= 0 else 0
        )
        out["ctr_same_level"] = heart_width / same_row_width if same_row_width else float("nan")
    else:
        out["ctr_same_level"] = float("nan")
    heart_bbox_w = out["heart_bbox_width_px"]
    lung_bbox_w = out["lung_bbox_width_px"]
    out["ctr_bbox"] = heart_bbox_w / lung_bbox_w if lung_bbox_w else float("nan")

    # ---- position (relevant to positioning/cropping shortcuts) ------------------
    hcx, hcy = _centroid(heart)
    lcx, lcy = _centroid(lung_union)
    out["heart_centroid_x_norm"] = hcx / w if w else float("nan")
    out["heart_centroid_y_norm"] = hcy / h if h else float("nan")
    out["lung_centroid_x_norm"] = lcx / w if w else float("nan")
    out["lung_centroid_y_norm"] = lcy / h if h else float("nan")

    for name, box in (("heart", (hy0, hx0, hy1, hx1)), ("lung", (ly0, lx0, ly1, lx1))):
        y0, x0, y1, x1 = box
        if x0 < 0:
            for side in ("left", "top", "right", "bottom"):
                out[f"{name}_bbox_{side}_norm"] = float("nan")
        else:
            out[f"{name}_bbox_left_norm"] = x0 / w
            out[f"{name}_bbox_top_norm"] = y0 / h
            out[f"{name}_bbox_right_norm"] = (w - 1 - x1) / w
            out[f"{name}_bbox_bottom_norm"] = (h - 1 - y1) / h

    # Does the segmentation touch the image border? Hints at cropping/collimation, and
    # at masks that were clipped by the field of view.
    out["lung_touches_border"] = bool(
        lung_union[0, :].any()
        or lung_union[-1, :].any()
        or lung_union[:, 0].any()
        or lung_union[:, -1].any()
    )

    if prefix:
        out = {f"{prefix}{k}": v for k, v in out.items()}
    return out
