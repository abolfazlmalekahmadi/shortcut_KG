"""RLE (run-length) encoding of CheXmask binary masks.

The encoding is the one published by the CheXmask authors in
``DataPostprocessing/utils.py`` of https://github.com/ngaggion/CheXmask-Database:

    def get_mask_from_RLE(rle, height, width):
        runs = np.array([int(x) for x in rle.split()])
        starts, lengths = runs[::2], runs[1::2]
        mask = np.zeros((height * width), dtype=np.uint8)
        for start, length in zip(starts, lengths):
            start -= 1                       # 1-based start positions
            mask[start:start + length] = 255
        return mask.reshape((height, width))

Two things follow from that reference implementation and matter for us:

* the flat index is **row-major** (``reshape((height, width))`` without an order
  argument), so ``index = y * width + x``;
* run starts are **1-based**.

``decode_rle`` reproduces the reference byte-for-byte but vectorised; ``decode_rle_ref``
is the literal reference, used by the test suite to check the fast path.
"""

from __future__ import annotations

import numpy as np

__all__ = ["decode_rle", "decode_rle_ref", "encode_rle"]


def _runs(rle: str) -> np.ndarray:
    """Parse ``"start length start length ..."`` into an int64 array."""
    if not rle or not rle.strip():
        return np.empty(0, dtype=np.int64)
    return np.array(rle.split(), dtype=np.int64)


def decode_rle_ref(rle: str, height: int, width: int) -> np.ndarray:
    """Reference decoder, copied verbatim from the CheXmask repository.

    Returns a ``(height, width)`` uint8 array with 0/255 values.
    """
    runs = _runs(rle)
    starts, lengths = runs[::2], runs[1::2]

    mask = np.zeros(height * width, dtype=np.uint8)
    for start, length in zip(starts, lengths):
        start -= 1  # 1-based
        mask[start : start + length] = 255
    return mask.reshape((height, width))


def decode_rle(rle: str, height: int, width: int) -> np.ndarray:
    """Vectorised decoder; identical output to :func:`decode_rle_ref`.

    Instead of painting every run, we build a difference array of run starts/ends and
    take its cumulative sum in one pass.
    """
    n = int(height) * int(width)
    runs = _runs(rle)
    if runs.size < 2:
        return np.zeros((height, width), dtype=np.uint8)

    starts = runs[0::2] - 1
    lengths = runs[1::2]
    ends = starts + lengths

    # Ignore defensive cases (should not occur in the published data): starts out of
    # range, or runs that run past the end of the raster.
    keep = (starts >= 0) & (starts < n) & (lengths > 0)
    starts, ends = starts[keep], np.minimum(ends[keep], n)
    if starts.size == 0:
        return np.zeros((height, width), dtype=np.uint8)

    diff = np.zeros(n + 1, dtype=np.int32)
    np.add.at(diff, starts, 1)
    np.add.at(diff, ends, -1)

    flat = np.cumsum(diff[:n]) > 0
    return (flat.reshape((height, width)) * 255).astype(np.uint8)


def encode_rle(mask: np.ndarray) -> str:
    """Encode a boolean/uint8 mask back to the same RLE string format.

    Used by the tests to check round-tripping. Row-major, 1-based starts.
    """
    flat = np.asarray(mask).reshape(-1) > 0
    padded = np.concatenate([[False], flat, [False]])
    changes = np.where(padded[1:] != padded[:-1])[0] + 1  # 1-based
    starts, lengths = changes[::2], changes[1::2] - changes[::2]
    return " ".join(str(int(v)) for v in np.stack([starts, lengths], axis=1).ravel())
