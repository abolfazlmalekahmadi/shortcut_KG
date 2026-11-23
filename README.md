# re-sp-in — anatomical measures from CheXmask (E1, first step)

Shortcut learning in medical imaging with knowledge graphs · Ines Tmimi & Abolfazl
Malekahmadi · supervision: Dr. Natalía Díaz-Rodríguez.

This repository holds the first slice of **E1**: turn the CheXmask heart / left-lung /
right-lung segmentation masks of an image into a small set of anatomical numbers
(heart width, lung areas, cardiothoracic ratio, plus frame-relative position), for a
small subset of each dataset. Those numbers are the anatomy half of the per-image
knowledge graph; the metadata half (sex, age, scanner, view, devices) joins onto them
later.

Nothing here trains a model or touches images. It is the measurement step only.

## What the numbers mean

Given the three masks of one image (size `H x W`):

| Measure | Definition |
|---|---|
| `heart_width_px` | maximal transverse cardiac diameter: widest horizontal extent of the heart mask |
| `thorax_width_px` | maximal inner thoracic diameter, approximated by the widest horizontal extent of the two lungs together |
| `ctr` | `heart_width_px / thorax_width_px` — the cardiothoracic ratio |
| `ctr_same_level` | heart width divided by the thoracic width **at the row** where the heart is widest |
| `ctr_bbox` | heart bounding-box width / lung bounding-box width |
| `*_area_px`, `*_area_frac` | mask area in pixels and as a fraction of the image |
| `heart_lung_area_ratio` | heart area / lung-union area |
| `lung_width_asymmetry` | `(left − right) / (left + right)` lung area |
| `*_width_norm`, `*_centroid_*_norm`, `*_bbox_*_norm` | position inside the image frame — the raw material for positioning / cropping / collimation shortcuts |
| `lung_touches_border` | the lung mask reaches the image edge (cropping or collimation) |

All of them are documented in the module docstring of
`src/chexmask_anatomy/measures.py`, which is the single source of truth.

**Pixel measures are not physical.** CheXmask ships no pixel spacing, and
`OriginalResolution` masks are at each source image's own size, so `heart_width_px` of
900 means nothing across images. Compare `ctr`, or the `*_frac` / `*_norm` variants.

## Quick start

```bash
# 200 VinDr-CXR images at native resolution + a figure of the first 4
python scripts/compute_anatomical_measures.py --dataset vindr --n 200 --plot 4

# 1000 random CheXpert images from the 1024x1024 grids
python scripts/compute_anatomical_measures.py --dataset chexpert \
    --variant preprocessed --n 1000 --sample random --seed 7

# both variants, every dataset, then the two reports
for ds in vindr chexpert mimic padchest chestxray8; do
  python scripts/compute_anatomical_measures.py --dataset $ds --variant original --n 200 --plot 4
done
for ds in vindr chexpert mimic padchest; do
  python scripts/compute_anatomical_measures.py --dataset $ds --variant preprocessed --n 200 --plot 4
done
python scripts/variant_agreement.py --out output/VARIANT_AGREEMENT.md
python scripts/summarise_runs.py --out output/CROSS_DATASET.md

# self-checks (RLE codec against the published reference, measures against a naive loop)
python tests/test_checks.py
```

Requirements: Python 3.10+, `numpy`, `pandas`, `matplotlib` (`pip install -r requirements.txt`).
No `opencv` needed.

## Layout

```
scripts/compute_anatomical_measures.py   CLI: masks of a subset -> CSV + summary JSON
scripts/compare_variants.py              two runs, side by side, per measure
scripts/variant_agreement.py             the same check for every dataset, -> one report
scripts/summarise_runs.py                every run in output/ -> one table
src/chexmask_anatomy/rle.py              RLE codec (row-major, 1-based, as the authors publish it)
src/chexmask_anatomy/measures.py         the measures
src/chexmask_anatomy/io.py               dataset registry, streaming CSV reader
tests/test_checks.py                     verification
data/                                    the CheXmask CSVs (see data/NOTES.md for provenance)
output/                                  results; each run writes <tag>.csv + <tag>.json
```

## Two caveats that cost time to discover

1. **`OriginalResolution` vs `Preprocessed`.** The release ships the same annotations
   twice: at native resolution, and padded-to-square then resized to 1024×1024. Anything
   that is a ratio of mask against mask (`ctr`, `heart_lung_area_ratio`, …) is identical
   in both — per image, agreement is 0.12–0.14% across the four datasets that ship both,
   and the rows are aligned image for image. Anything normalised by the *image frame*
   (`*_area_frac`, `*_centroid_*_norm`, `image_aspect`) shifts by up to 99%, because
   `Preprocessed` changed the frame. **Use `OriginalResolution` for positioning
   questions**; either is fine for CTR. `output/VARIANT_AGREEMENT.md` is the evidence.

2. **Quality threshold.** `Dice RCA (Mean) ≥ 0.7` is the authors' recommendation. Rows
   below it are kept in the CSV but flagged with `quality_ok = false`, and the summary
   statistics are computed on the passing rows only.

## Data

`data/` holds all five `OriginalResolution` CSVs and four `Preprocessed` CSVs
(~38 GB), fetched from the Hugging Face mirror `ming0100/chexmask` and checksum-verified
against the release's `SHA256SUMS.txt`. PhysioNet blocks this region, so the mirror is
the only route from here. See `data/NOTES.md`.

## First results (first 200 rows of each dataset, both released rasters)

Same code, same images, two grids. Full tables: `output/CROSS_DATASET.md` and
`output/VARIANT_AGREEMENT.md`; per-run CSVs and JSON summaries in `output/`.

| dataset | n | ok | CTR `OriginalResolution` | CTR `Preprocessed` | CTR p05–p95 | heart width | lung area |
|---|---:|---:|---|---|---|---|---|
| MIMIC-CXR-JPG | 200 | 194 | 0.509 ± 0.059 | 0.510 ± 0.059 | 0.420–0.612 | 1,038 px | 23.7% |
| CheXpert | 200 | 200 | 0.498 ± 0.054 | 0.498 ± 0.054 | 0.416–0.593 | 980 px | 25.4% |
| VinDr-CXR | 200 | 199 | 0.487 ± 0.051 | 0.488 ± 0.051 | 0.402–0.577 | 906 px | 23.5% |
| ChestX-Ray8 | 200 | 198 | 0.467 ± 0.058 | — (not shipped) | 0.380–0.573 | 349 px | 24.0% |
| PadChest | 200 | 198 | 0.455 ± 0.061 | 0.455 ± 0.061 | 0.364–0.560 | 791 px | 26.1% |

Heart width and lung area are quoted for `OriginalResolution` only; the `Preprocessed`
figures are pixel counts on a 1024×1024 grid and are not comparable to them.

Four things worth noticing already:

- **The two grids agree, exactly where it matters.** Per image, CTR differs between
  `OriginalResolution` and `Preprocessed` by 0.12–0.14% (r ≥ 0.9999) on all four datasets
  that ship both. See `output/VARIANT_AGREEMENT.md`.
- **CTR separates the datasets** (0.455 to 0.509 — a 0.054 span between dataset means)
  about as much as it separates images inside one dataset (sd ≈ 0.05). In other words,
  knowing *which dataset* an image comes from is worth about as much as knowing anything
  about the patient: a centre-level signal of exactly the kind the project wants to name
  and measure.
- **Every dataset has a tail of large hearts**: p95 is 0.56–0.61 against a clinical
  threshold of 0.5. Any shortcut analysis has to keep that physiological variation
  separate from whatever it is chasing.
- **The rows are aligned across the two variants**, image for image and in the same
  order, so the per-image comparison above needs no join. Ids are *not* unique per
  patient though: the first three CheXpert rows are three studies of `patient40255`.

Figures of the decoded masks, for both variants of each dataset, are in
`output/figures/` (red = patient's right lung, green = patient's left lung, blue = heart).

## Next

- Extend from 200 rows to the full release (~657k masks across the five datasets).
- Join the measures to acquisition metadata and demographics (E1 continues); the
  frame-relative columns are the ones to test for positioning shortcuts.
- Add the landmark-derived measures (`Landmarks` is parsed already) if contours are
  wanted on top of areas.
