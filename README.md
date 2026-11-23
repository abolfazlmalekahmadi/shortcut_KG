# shortcut_KG — anatomical measures from CheXmask (E1, first step)

Shortcut learning in medical imaging with knowledge graphs · Ines Tmimi & Abolfazl
Malekahmadi · supervision: Dr. Natalía Díaz-Rodríguez.

This repository holds the first slice of **E1**: turn the CheXmask heart / left-lung /
right-lung segmentation masks of an image into a small set of anatomical numbers
(heart width, lung areas, cardiothoracic ratio, plus frame-relative position). Those
numbers are the anatomy half of the per-image knowledge graph; the metadata half
(sex, age, scanner, view, devices) joins onto them later.

It has been run over **every image of all five datasets** — 657,463 masks at native
resolution and 545,343 on the preprocessed grids — in about four minutes.

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

# the same subset from the fixed 1024x1024 grids
python scripts/compute_anatomical_measures.py --dataset vindr \
    --variant preprocessed --n 200 --plot 4

# every row of a dataset (omit --n, or pass --n 0)
python scripts/compute_anatomical_measures.py --dataset mimic --variant preprocessed

# both variants, every dataset, then the two reports
python scripts/run_full.py
python scripts/summarise_runs.py --glob 'output/full/*.json' --out output/FULL_DATASET.md
python scripts/variant_agreement.py --output-dir output/full --out output/FULL_VARIANT_AGREEMENT.md

# 1000 random CheXpert images
python scripts/compute_anatomical_measures.py --dataset chexpert \
    --variant preprocessed --n 1000 --sample random --seed 7

# re-derive a few rows of a finished full run from the source, with the raster engine
python scripts/verify_run.py --csv output/full/mimic_original.csv \
    --dataset mimic --variant original --n 5

# self-checks: the codec against the authors' decoder, the measures against a naive
# loop, and the fast engine against the raster engine
python tests/test_checks.py
python tests/test_fast_engine.py
```

Requirements: Python 3.10+, `numpy`, `pandas`, `matplotlib` (`pip install -r requirements.txt`).
No `opencv` needed.

## Two engines, one set of numbers

| | `measures.measure_masks` (raster) | `measures_rle.measure_rle` (fast) |
|---|---|---|
| how | decodes the three masks to pixel arrays | works on the run lists directly |
| speed | ~3 rows/s at native resolution | ~1,500 rows/s |
| role | the readable reference for every definition | what the full-dataset runs use |

They are interchangeable: `--engine fast|raster` selects one, the CLI writes the same 45
columns either way, and `tests/test_fast_engine.py` compares every measure on 365 real
images from all five datasets, on 44 images whose masks are not contiguous, and on
synthetic rows with an empty organ.

## Layout

```
scripts/compute_anatomical_measures.py   CLI: a subset or a whole dataset -> CSV + summary JSON
scripts/run_full.py                      the nine full passes, several at a time
scripts/compare_variants.py              two runs, side by side, per measure
scripts/variant_agreement.py             the same check for every dataset, -> one report
scripts/summarise_runs.py                every run in output/ -> one table
scripts/describe_runs.py                 distributions, data quality, effect sizes, confounders
scripts/verify_run.py                    re-derive rows of a finished run with the raster engine
src/chexmask_anatomy/rle.py              RLE codec (row-major, 1-based, as the authors publish it)
src/chexmask_anatomy/measures.py         the raster engine / the definitions
src/chexmask_anatomy/measures_rle.py     the run-based engine
src/chexmask_anatomy/io.py               dataset registry, streaming CSV reader
tests/test_checks.py                     codec and measures
tests/test_fast_engine.py                fast engine against the raster engine
data/                                    the CheXmask CSVs (see data/NOTES.md for provenance)
output/                                  the 200-row sample runs (CSV + JSON + figures)
output/full/                             the full runs (JSON committed, CSV not)
```

## Four caveats that cost time to discover

1. **`OriginalResolution` vs `Preprocessed`.** The release ships the same annotations
   twice: at native resolution, and padded-to-square then resized to 1024×1024. Anything
   that is a ratio of mask against mask (`ctr`, `heart_lung_area_ratio`, …) is identical
   in both — per image, agreement is 0.12–0.14% over 545,343 paired images. Anything
   normalised by the *image frame* (`*_area_frac`, `*_centroid_*_norm`, `image_aspect`)
   shifts by up to 102%, because `Preprocessed` changed the frame: `lung_touches_border`
   alone drops from 8,028 to 930 on CheXpert. **Use `OriginalResolution` for positioning
   questions**; either is fine for CTR. `output/FULL_VARIANT_AGREEMENT.md` is the evidence.

2. **Quality threshold.** `Dice RCA (Mean) ≥ 0.7` is the authors' recommendation. Rows
   below it are kept in the CSV but flagged with `quality_ok = false`, and the summary
   statistics are computed on the passing rows only.

3. **A row of a mask is not always one contiguous stretch of pixels**, and some rows ship
   an empty organ (49 rows in MIMIC-CXR-JPG, one in PadChest). Neither assumption is safe;
   the fast engine makes neither, and both cases are covered in `tests/test_fast_engine.py`.

4. **`OriginalResolution` is not native for ChestX-Ray8.** All 112,120 of its rows are
   1024×1024, i.e. it ships the square-padded grid under the "original" name, so
   frame-relative measures for that dataset are on the padded frame whatever variant is
   asked for. Every other dataset is genuinely native here: 6,486 distinct sizes in
   VinDr-CXR, 6,978 in CheXpert, 16,656 in MIMIC-CXR-JPG, 33,383 in PadChest.

## Data

`data/` holds all five `OriginalResolution` CSVs and four `Preprocessed` CSVs
(~38 GB), fetched from the Hugging Face mirror `ming0100/chexmask` and checksum-verified
against the release's `SHA256SUMS.txt`. PhysioNet blocks this region, so the mirror is
the only route from here. See `data/NOTES.md`.

## Results — every image of every dataset

Nine passes, 1.2 M masks, 260 s of wall clock (six at a time). Readings are the
`quality_ok` rows; full tables in `output/FULL_DATASET.md` and
`output/FULL_VARIANT_AGREEMENT.md`.

| dataset | images | quality-fail | CTR `OriginalResolution` | CTR `Preprocessed` | CTR p05–p95 | lung area | heart/lung area |
|---|---:|---:|---|---|---|---|---:|
| MIMIC-CXR-JPG | 243,334 | 2.4% | 0.509 ± 0.067 | 0.510 ± 0.067 | 0.403–0.620 | 23.8% | 0.455 |
| CheXpert | 187,825 | 0.6% | 0.504 ± 0.059 | 0.504 ± 0.059 | 0.409–0.604 | 24.5% | 0.438 |
| ChestX-Ray8 | 112,120 | 1.2% | 0.471 ± 0.061 | — (not shipped) | 0.382–0.579 | 24.5% | 0.381 |
| PadChest | 96,184 | 1.3% | 0.460 ± 0.060 | 0.460 ± 0.060 | 0.373–0.570 | 25.9% | 0.365 |
| VinDr-CXR | 18,000 | 0.5% | 0.481 ± 0.052 | 0.482 ± 0.052 | 0.403–0.573 | 24.0% | 0.360 |
| **total** | **657,463** | **1.4%** | | | | | |

`lung area` and `heart/lung area` are quoted for `OriginalResolution` only; their
`Preprocessed` values are other numbers on a 1024×1024 grid.

What the numbers say so far:

- **The row count cross-checks against the release**: 657,463 masks counted, against the
  657,566 the dataset README advertises — 0.02% apart, the mirror being v1.0.1.
- **CTR ranks the datasets** — 0.460 (PadChest) to 0.510 (MIMIC). That 0.050 span is
  about the size of the spread *inside* a dataset (sd 0.052–0.067). Knowing which dataset
  an image comes from is therefore worth about as much as knowing anything about the
  patient: a centre-level signal of the kind the project wants to name and measure.
- **A 200-row sample can mislead.** On the first 200 CheXpert rows CTR read 0.498; on all
  187,825 it reads 0.504, because the head of the file is a handful of patients — the
  first three rows are three studies of `patient40255`. Sample before trusting a subset.
- **Quality is unevenly distributed**: 0.5% of VinDr rows fail the Dice threshold and
  2.4% of MIMIC rows do, so MIMIC's anatomical half will be the noisiest to join.
- **Every dataset has a large-heart tail** — p95 between 0.57 and 0.62, up to 0.82 —
  against a clinical threshold of 0.5. Any shortcut analysis has to keep that
  physiological variation apart from what it is chasing.
- **The share of "cardiomegaly by threshold" is wildly dataset-dependent**: CTR > 0.5 in
  22.9% of PadChest, 29.7% of ChestX-Ray8, 33.0% of VinDr, 51.5% of CheXpert and 54.5% of
  MIMIC. A 2.4× spread in a ratio that is supposed to be physiological is more plausibly
  technique and case mix than epidemiology.
- **The gap is not just magnification.** `heart_lung_area_ratio` is a ratio of two areas in
  the same image, so global scale cancels in it, and it still separates the datasets by up
  to 0.67 within-dataset standard deviations (CheXpert, MIMIC) — more than CTR does (0.42).
- **CTR moves with lung expansion, in every dataset**: `r(CTR, lung_area_frac)` is −0.48
  (CheXpert), −0.57 (ChestX-Ray8), −0.57 (PadChest), −0.58 (VinDr) and −0.61
  (MIMIC-CXR-JPG). In other words the cardiothoracic ratio measured here is not only heart
  size — a poorly inspired or differently positioned film raises it — while
  `r(CTR, image size)` is only +0.06…+0.15, so detector size is not what drives it. This is
  the first mechanism the knowledge graph should be able to name.

`output/FULL_DIAGNOSTICS.md` has the distributions, effect sizes and correlations behind
these statements; 49 MIMIC rows ship an empty organ and drop out of the ratios.

Figures of the decoded masks, for both variants of each dataset, are in
`output/figures/` (red = patient's right lung, green = patient's left lung, blue = heart).
The 200-row sample runs and their two reports (`output/CROSS_DATASET.md`,
`output/VARIANT_AGREEMENT.md`) are kept beside them for quick iteration.

## Next

- Join the measures to acquisition metadata and demographics (E1 continues); the
  frame-relative columns are the ones to test for positioning shortcuts.
- That join needs MIMIC-CXR DICOM and MIMIC-IV demographics, which require PhysioNet
  credentialing (CITI course) — blocked from this IP, same as the masks were.
- Add the landmark-derived measures (`Landmarks` is parsed already) if contours are
  wanted on top of areas.
