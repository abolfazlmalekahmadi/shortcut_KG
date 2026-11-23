# CheXmask data — local copy

Anatomical segmentation masks (heart / left lung / right lung) for chest X-rays, used
in **E1** of the project brief (per-image anatomical measures: lung areas, heart width,
cardiothoracic ratio).

## Source

- **Original:** PhysioNet — `chexmask-cxr-segmentation-data` v1.0.0
  <https://physionet.org/content/chexmask-cxr-segmentation-data/1.0.0/>
  License: **CC BY 4.0** — *"Anyone can access the files, as long as they conform to
  the terms of the specified license."*
- **This copy was fetched from the Hugging Face mirror** `ming0100/chexmask`
  (CheXmask Database v1.0.1). PhysioNet returns `403 Forbidden` for requests from an
  Iranian IP — *"Data is not available in your region due to legal or policy
  restrictions."* DNS and TLS to PhysioNet are fine; it is an IP/region block, not a
  network problem.
  <https://huggingface.co/datasets/ming0100/chexmask>

Every CSV was verified against the official `SHA256SUMS.txt`; all hashes match.

## Layout

```
data/
├── OriginalResolution/    # masks at each image's native pixel size
│   ├── CheXpert.csv            8.8 GB
│   ├── ChestX-Ray8.csv         2.1 GB
│   ├── MIMIC-CXR-JPG.csv        13 GB
│   ├── Padchest.csv            4.3 GB
│   └── VinDr-CXR.csv           902 MB
├── Preprocessed/          # masks resampled to a fixed size (see below)
│   ├── CheXpert.csv            3.0 GB
│   ├── MIMIC-CXR-JPG.csv       4.0 GB
│   ├── Padchest.csv            1.7 GB
│   └── VinDr-CXR.csv           310 MB
├── DATA_DICTIONARY.md
├── LICENSE.txt
├── SHA256SUMS.txt
├── README.md          # the mirror's own README, kept verbatim (see below)
└── NOTES.md           # this file
```

`Preprocessed/` has **no `ChestX-Ray8.csv`** (the mirror only ships four datasets
there). `OriginalResolution/` has all five.

## Checksums

OriginalResolution:

| File | SHA256 |
|---|---|
| `CheXpert.csv`       | `dc48369ba61c87bed9b0e34c22e05b360acfaaf65ce75bd06c53c60d6478dd90` |
| `ChestX-Ray8.csv`    | `48766ab0268235d63666bb2bacbd9f642b33fce7c1be40b9e1ecb381605545fa` |
| `MIMIC-CXR-JPG.csv`  | `3700b5502e4733b9665b8f071dedb833ab449006caa1dc4ecb2a42eef716346c` |
| `Padchest.csv`       | `89e8aed4ea92befdd394a4b5c6423cb8d895f3e24bd3092dd150938082922fed` |
| `VinDr-CXR.csv`      | `e23b819a3709af22fce84cd7359b0b5b0d6d00037bd3996fbc9b958611961b5b` |

Preprocessed:

| File | SHA256 |
|---|---|
| `CheXpert.csv`       | `6b683b1f8fa4f8762b953d3f235ccdfa995ff2a5b3ec757e30ebc472c6e209e1` |
| `MIMIC-CXR-JPG.csv`  | `3ff83ca9731c34dc17d448acf48adecaddf4f2a76e7b4047f46039efd94935d6` |
| `Padchest.csv`       | `e9058e49aca959b4e8e4a73cff2609b1f5f986088f3cd200b2e41cd5b02f923c` |
| `VinDr-CXR.csv`      | `6fad806fa89026d9df81ec8ae6207c11fa095077aebab303cc94b407b18b29ac` |

Verify with `SHA256SUMS.txt` (keys are the mirror's own paths):

```bash
cd "$(dirname "$0")" && sha256sum -c SHA256SUMS.txt
```

All 11 entries must print `OK`. `README.md` in this folder is the mirror's README kept
verbatim so that check passes; the notes you are reading are in `NOTES.md`.

## Format (see `DATA_DICTIONARY.md`)

Column layout is identical in both variants:

```
<id>, Dice RCA (Mean), Dice RCA (Max), Landmarks, Left Lung, Right Lung, Heart, Height, Width
```

- First column is the join key, but **its name differs per dataset**:

  | Dataset | ID column | Joins to |
  |---|---|---|
  | `CheXpert.csv` | `Path` | CheXpert image path |
  | `ChestX-Ray8.csv` | `Image Index` | NIH ChestX-ray8 file name |
  | `MIMIC-CXR-JPG.csv` | `dicom_id` | MIMIC-CXR-JPG `dicom_id` |
  | `Padchest.csv` | `ImageID` | PadChest image ID |
  | `VinDr-CXR.csv` | `image_id` | VinDr-CXR image ID |

- First column is also **not row-aligned across datasets**; each dataset is its own CSV.
- `Left Lung` / `Right Lung` / `Heart` are **RLE**-encoded binary masks; decode with the
  same row's `Height` / `Width`.
- `Landmarks` is a newline-separated JSON array of `[x, y]` pixel coordinates.
- `Dice RCA (Mean/Max)` is segmentation quality; the authors recommend keeping rows with
  **Mean ≥ 0.7**.

### `OriginalResolution` vs `Preprocessed`

- `OriginalResolution` — mask stored at the native size of the source image, so
  `Height`/`Width` differ per row and pixel sizes are **not comparable across images**.
  Use it when you have (or want) the original image pixel grid.
- `Preprocessed` — every mask resampled to a **fixed grid**, so masks are directly
  comparable across images and cheaper to decode. Preferred for measures like
  cardiothoracic ratio if you do not need pixel-space absolute sizes.

  **Caveat** (measured on 200 VinDr-CXR images, see `scripts/compare_variants.py`):
  padding each image to a square changes the frame, so anything normalised by the image
  frame drifts — `*_area_frac` and `*_width_norm` by ~13%, `image_aspect` becomes
  identically 1.0. Mask-against-mask ratios (CTR, heart/lung area ratio) are unaffected
  (agreement < 0.2%). Use `OriginalResolution` for positioning / cropping questions.

## Notes

- MIMIC-CXR images/DICOM and MIMIC-IV demographics need PhysioNet credentialing
  (CITI course); that path is region-blocked from this IP too.
