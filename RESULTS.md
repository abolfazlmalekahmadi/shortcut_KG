# Results — E1, step 1: anatomical measures from CheXmask masks

**Status:** complete for this step. Every number below is produced by the code in this
repository, from the data described in §1, and the commands are in §9.
**Date:** 23 November 2026 · Ines Tmimi & Abolfazl Malekahmadi

This is the first step of **E1** in the project brief: turn the CheXmask heart /
left-lung / right-lung segmentation masks of an image into per-image anatomical numbers,
so they can later be joined into the per-image knowledge graph.

**No model is trained, no label is used, and no image is read.** Nothing here is a
statement about shortcuts; it is the measurement layer those statements will need, plus
what that layer already reveals about the data.

---

## 1. Data

| | |
|---|---|
| source | CheXmask Database v1.0.1, Hugging Face mirror `ming0100/chexmask` |
| why the mirror | PhysioNet serves this region `403 Forbidden` — *"Data is not available in your region due to legal or policy restrictions"*. DNS and TLS to PhysioNet are fine; it is an IP block. The mirror was used instead and every file was checked against the release's own `SHA256SUMS.txt`. |
| integrity | 13/13 checksums match (`sha256sum -c SHA256SUMS.txt`) |
| size on disk | 37.3 GiB, 9 CSVs |
| licence | CC BY 4.0 (dataset) |

Two published rasters of the same annotations:

- `OriginalResolution` — masks on each source image's native grid. Five datasets.
- `Preprocessed` — masks padded to a square and resized to 1024×1024. Four datasets
  (ChestX-Ray8 is not shipped in this variant).

**Coverage** (native resolution; the preprocessed counts are identical where the variant
exists):

| dataset | rows | quality-fail | distinct grids | median grid |
|---|---:|---:|---:|---|
| MIMIC-CXR-JPG | 243,334 | 2.40% | 16,656 | 2544×2734 |
| CheXpert | 187,825 | 0.55% | 6,978 | 2828×2320 |
| ChestX-Ray8 | 112,120 | 1.18% | **1** | 1024×1024 |
| PadChest | 96,184 | 1.31% | 33,383 | 2000×1884 |
| VinDr-CXR | 18,000 | 0.47% | 6,486 | 2361×2836 |
| **total** | **657,463** | **1.45%** | | |

1,202,806 masks in total across the two variants. Processing all of them takes 260 s of
wall clock (nine passes, six at a time).

---

## 2. Measures

45 columns per image. The definitions are the single source of truth in the module
docstring of `src/chexmask_anatomy/measures.py`; in short:

| group | columns | note |
|---|---|---|
| identity | `dataset`, `variant`, `image_id`, `height`, `width`, `image_aspect` | |
| segmentation quality | `quality_ok`, `dice_rca_mean`, `dice_rca_max` | `quality_ok` = Dice RCA mean ≥ 0.7, the authors' recommendation |
| areas | `heart_area_px`, `left_lung_area_px`, `right_lung_area_px`, `lung_area_px` (union), and the same four as `*_frac` of the image | |
| widths | `heart_width_px` (maximal transverse cardiac diameter), `thorax_width_px` (maximal inner thoracic diameter, taken from the lung union), per-lung and bounding-box widths, and `*_norm` variants | |
| ratios | `ctr`, `ctr_same_level`, `ctr_bbox`, `heart_lung_area_ratio`, `lung_width_asymmetry` | **only these are invariant to the frame**; see §4.4 |
| position | `*_centroid_*_norm`, `*_bbox_*_norm`, `lung_touches_border` | frame-relative — the raw material for positioning / cropping / collimation shortcuts |

**Pixel widths are not physical.** CheXmask ships no pixel spacing and the native grids
differ by dataset, so `heart_width_px` is comparable only within one grid. Ratios and
`*_frac` / `*_norm` are the comparable forms.

---

## 3. Method and verification

Two engines compute the same 45 numbers:

| | `measures.measure_masks` (raster) | `measures_rle.measure_rle` (fast) |
|---|---|---|
| how | decodes the three masks to pixel arrays | works on the run lists directly |
| speed | ~3 rows/s at native resolution | ~1,500 rows/s |
| role | the readable reference | what the full runs use |

Four independent checks:

1. **Decoder** against the implementation the CheXmask authors publish
   (`get_mask_from_RLE` in their repository) — byte-identical output.
2. **Raster measures** against a naive row-by-row loop.
3. **Fast engine against the raster engine**: all 45 columns on 365 real images drawn
   from all five datasets, on 44 images whose masks are not contiguous, and on 40
   synthetic rows with an empty organ.
4. **Finished runs against the source**: rows of the committed full-run tables re-derived
   from the source CSV with the raster engine (`scripts/verify_run.py`) — every column
   identical.

Two mistakes that only the full run exposed, and that are now covered by tests: a row of
a mask is **not** always one contiguous interval (301 such rows in a small sample), and 49
MIMIC rows carry an annotation with no pixels at all.

---

## 4. Results

All readings are on `quality_ok` rows of the native-resolution grids unless stated.

### 4.1 Data quality

- 9,537 rows (1.45%) fail Dice RCA mean ≥ 0.7. The rate is uneven: 0.47% in VinDr-CXR,
  2.40% in MIMIC-CXR-JPG. That is the noise floor of any downstream join.
- **`quality_ok` is not a sufficient filter.** 49 MIMIC-CXR-JPG rows annotate nothing at
  all — heart, left lung and right lung all empty — and 46 of them pass Dice RCA ≥ 0.7
  (values 0.65–0.89). The published quality metric does not flag an empty annotation, and
  CTR is undefined for those rows. Downstream code must require non-zero areas (or a
  finite `ctr`) explicitly. One PadChest row has an empty right lung.
- Full row counts: 657,463 mask annotations, against the **657,566** the dataset README
  advertises. 103 rows (0.02%) short; unexplained (see §7).

### 4.2 CTR distributions

| dataset | n | CTR p10 | median | p90 | CTR > 0.5 | CTR > 0.6 |
|---|---:|---:|---:|---:|---:|---:|
| MIMIC-CXR-JPG | 237,498 | 0.423 | 0.508 | 0.596 | 54.5% | 9.0% |
| CheXpert | 186,791 | 0.428 | 0.502 | 0.581 | 51.5% | 5.6% |
| VinDr-CXR | 17,915 | 0.418 | 0.477 | 0.549 | 33.0% | 2.1% |
| ChestX-Ray8 | 110,795 | 0.398 | 0.466 | 0.552 | 29.7% | 2.8% |
| PadChest | 94,927 | 0.389 | 0.454 | 0.541 | 22.9% | 2.1% |

Every dataset has a large-heart tail, and the share above the clinical threshold of 0.5
ranges from 22.9% to 54.5% — a 2.4× spread in a ratio that is supposed to be
physiological. Read as epidemiology that is implausible; technique and case mix are the
obvious alternatives.

### 4.3 Between-dataset differences

Effect size `d` = difference of dataset means divided by the pooled within-dataset
standard deviation, relative to VinDr-CXR.

| dataset | CTR | d(CTR) | heart / lung area | d(h/l area) | lung area (frac of image) |
|---|---:|---:|---:|---:|---:|
| MIMIC-CXR-JPG | 0.509 ± 0.067 | +0.42 | 0.455 ± 0.145 | +0.67 | 23.8% |
| CheXpert | 0.504 ± 0.059 | +0.38 | 0.438 ± 0.122 | +0.66 | 24.5% |
| VinDr-CXR | 0.481 ± 0.052 | — | 0.360 ± 0.091 | — | 24.0% |
| ChestX-Ray8 | 0.471 ± 0.061 | −0.17 | 0.381 ± 0.118 | +0.18 | 24.5% |
| PadChest | 0.460 ± 0.060 | −0.36 | 0.365 ± 0.104 | +0.06 | 25.9% |

Two things matter here.

- The dataset gap in CTR is about 0.4 standard deviations — real, but of the same order as
  the patient-to-patient spread inside one dataset. Knowing the centre is worth roughly as
  much as knowing something about the patient.
- `heart_lung_area_ratio` separates the datasets *more* strongly than CTR (±0.66 vs
  ±0.42), and it is a ratio of two areas in the same image, so any global magnification
  cancels in it. The between-dataset difference is therefore not only magnification.

### 4.4 The two published rasters agree, where it matters

Over 545,343 images that ship in both variants:

| | per-image mean absolute relative difference |
|---|---|
| `ctr` | 0.12–0.14% (Pearson r 0.9977–1.0000) |
| `ctr_bbox`, `heart_lung_area_ratio`, `lung_width_asymmetry` | 0.06–1.49% |
| frame-normalised measures (`*_area_frac`, `*_centroid_*_norm`, `*_bbox_*_norm`, `image_aspect`) | 0.0–102% |

So: mask-against-mask ratios may be computed on either grid, and are indifferent to
CheXmask's own padding and resizing. Frame-relative measures may not be mixed across
grids — they move with the frame, not with the patient (`lung_touches_border` alone falls
from 8,028 to 930 on CheXpert). The second point also settles a control for everything
above: the between-dataset differences live in the masks, not in CheXmask's pipeline.
The rows are also aligned image-for-image across the two variants, so this comparison
needed no join.

### 4.5 CTR is not only heart size

Within each dataset, `ctr` co-varies with how much of the frame the lungs occupy:

| dataset | r(CTR, width) | r(CTR, lung area) | r(thorax width, lung area) | r(heart width, lung area) | partial r(CTR, lung area \| thorax width) |
|---|---:|---:|---:|---:|---:|
| MIMIC-CXR-JPG | +0.080 | −0.606 | +0.547 | −0.195 | −0.546 |
| VinDr-CXR | +0.058 | −0.579 | +0.669 | +0.077 | −0.593 |
| ChestX-Ray8 | — | −0.574 | +0.597 | −0.119 | −0.489 |
| PadChest | +0.097 | −0.567 | +0.575 | −0.075 | −0.569 |
| CheXpert | +0.144 | −0.482 | +0.548 | −0.076 | −0.431 |

Part of this is tautological — the thorax width sits in the CTR denominator and moves with
lung area — so the partial correlation controlling for thorax width is the number to read.
It is −0.43 to −0.59 in all five datasets, and heart width itself is essentially unrelated
to lung area. The coupling runs through how tall and expanded the lungs are, and how the
film is framed, rather than through the heart. Meanwhile `r(CTR, image size)` is only
+0.06 to +0.14: detector size is not what drives it.

In other words, **CTR as measured here is not an isolated measure of heart size — it is a
confounder as much as a feature**, and the direction of the effect is clinically familiar
(inspiration, projection and habitus all move it).

### 4.6 How much of the centre is already in the anatomy

A logistic regression on the measures alone — no image, no metadata, no model beyond a
linear classifier — predicting which of two datasets an image comes from, 5-fold
stratified CV, 20,000 random quality-ok images per dataset.

| pair | frame-invariant features only | all anatomy features |
|---|---:|---:|
| CheXpert vs ChestX-Ray8 | 0.663 | **0.963** |
| CheXpert vs PadChest | 0.722 | 0.880 |
| MIMIC-CXR-JPG vs PadChest | 0.715 | 0.834 |
| MIMIC-CXR-JPG vs ChestX-Ray8 | 0.671 | 0.769 |
| MIMIC-CXR-JPG vs CheXpert | 0.579 | 0.886 |
| ChestX-Ray8 vs PadChest | 0.573 | 0.811 |

The left column uses only ratios of a mask against itself, so it survives any rescaling or
change of frame: a dataset named from those alone is named by its **anatomy**. That column
sits at 0.57–0.72, and CTR alone gives 0.52–0.71 — i.e. essentially all of the genuinely
anatomical signal is the moderate CTR difference of §4.3.

The right column's near-perfect values are the **file format** answering, not the patient:
ChestX-Ray8 ships every one of its 112,120 masks at 1024×1024. This is a concrete
injunction: frame-relative columns must never be compared across datasets.

---

## 5. What this step establishes

1. The measurement layer of E1 works, is exact, and is reproducible at the scale of the
   whole release (1.2 M masks, 260 s, four independent levels of verification, and the
   command recorded in every run summary).
2. Two decisions are now evidence-based rather than stylistic: ratios of mask against mask
   may be taken from either published raster; frame-relative measures may only be taken
   from `OriginalResolution`, and never compared across datasets (and for ChestX-Ray8 even
   `OriginalResolution` is the padded 1024×1024 grid).
3. `quality_ok` (Dice ≥ 0.7) is necessary but not sufficient: 46 MIMIC rows carry an empty
   annotation and still pass it. Downstream joins must also require non-zero areas.
4. There is a real but **moderate** centre-level signal in chest anatomy: ~0.4 standard
   deviations in CTR, up to 0.67 in the scale-invariant heart/lung area ratio, and an
   AUC of 0.57–0.72 for naming the dataset from frame-invariant measures alone.
5. CTR is coupled to lung extent (partial r ≈ −0.5 in every dataset) and not to detector
   size, so it is a confounder as much as a feature.

## 6. What this step does **not** establish

- **Nothing about shortcuts.** No model was trained, no label was used, and no image was
  read. A dataset being predictable from anatomy is not evidence of an artifact: age, sex
  and disease mix differ between these datasets and would legitimately move heart size.
- Which of the plausible mechanisms produces the centre signal. At least three remain open,
  and can only be separated with metadata this step did not touch: **projection** (CTR is
  only valid on PA erect films, and MIMIC-CXR and CheXpert are enriched for AP portable
  views), **inspiration / positioning / habitus** (§4.5), and **case mix** (age, sex,
  indication; MIMIC-CXR is an ICU cohort).
- Anything about images, acquisition parameters, devices, or patient groups. Those are the
  other half of E1.

## 7. Open items

- **103 missing rows** (657,463 measured vs 657,566 advertised, 0.02%). The mirror is
  v1.0.1 and the advertised count may be v1.0.0; not resolved.
- **Empty annotations pass the quality metric** (§4.1). Worth reporting to the CheXmask
  authors: Dice RCA ≥ 0.7 on a mask with no pixels suggests the metric is computed in a way
  that cannot see this case.
- **`image_id` is not unique per patient.** The first three CheXpert rows are three studies
  of `patient40255`, so any join to demographics or metadata must aggregate to the patient
  level first.
- **Subsets taken from the head of these files are not representative.** The first 200 rows
  of CheXpert give a CTR of 0.498; all 187,825 give 0.504. The files are grouped by patient
  and study. Draw subsets across the file, never from the front — this directly affects the
  "small subset first" workflow.

---

## 8. Next experiments

Each is cheap and each has a clear outcome either way.

1. **Is the centre signal projection?** Split MIMIC-CXR and CheXpert by view (AP vs PA) and
   recompute CTR within each stratum. If the between-dataset CTR gap collapses, the
   anatomical centre signal is technique, and every CTR-based feature must be
   view-conditioned. If it survives, it is a candidate for E2.
2. **What is left of CTR once the confounders are out?** Regress CTR on view, lung extent
   (`lung_area_frac`), age and sex, and treat the residual as the "heart size" component.
   This is the version of the measure that should enter the graph.
3. **Close E1.** Join the acquisition metadata (view, device, exposure) and demographics
   (age, sex — MIMIC-IV, CheXpert Plus) onto these columns, and re-run the §4.6 test with
   the metadata included, to see whether the anatomy-only AUC of 0.57–0.72 is explained.
   MIMIC-CXR DICOM and MIMIC-IV require PhysioNet credentialing, which is blocked from
   this IP — the same block as the masks; credentialed access from a permitted network will
   be needed.

## 9. Artefacts and how to reproduce

| artefact | content |
|---|---|
| `output/FULL_DATASET.md` | one row per dataset and variant: n, quality-ok, headline statistics |
| `output/FULL_DIAGNOSTICS.md` | §4.1, §4.2, §4.3, §4.5 |
| `output/FULL_VARIANT_AGREEMENT.md` | §4.4, per measure |
| `output/DATASET_LEAKAGE.md` | §4.6 |
| `output/full/*.json` | nine run summaries, each recording the exact command, versions, row counts and elapsed time |
| `output/full/*.csv` | the per-image tables themselves, 657,463 and 545,343 rows × 45 columns (~700 MB total, not committed) |
| `output/*_n200.*`, `output/figures/` | 200-row sample runs and mask overlays, for quick iteration |

```bash
python scripts/run_full.py
python scripts/summarise_runs.py --glob 'output/full/*.json' --out output/FULL_DATASET.md
python scripts/variant_agreement.py --output-dir output/full --out output/FULL_VARIANT_AGREEMENT.md
python scripts/describe_runs.py --out output/FULL_DIAGNOSTICS.md
python scripts/dataset_leakage.py --out output/DATASET_LEAKAGE.md
python tests/test_checks.py && python tests/test_fast_engine.py
```
