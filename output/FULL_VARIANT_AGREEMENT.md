# OriginalResolution vs Preprocessed — do the measures agree?

Same code, same images, two published rasters. `mean abs rel diff` is the mean of `|B - A| / A` over the images the two runs share, so `0.2%` means the two grids give, on average, a value 0.2% away from each other.

| dataset | images | CTR r | CTR mean abs rel diff | worst mask-vs-mask ratio | frame-normalised drift |
|---|---:|---:|---:|---|---|
| vindr | 18000 | 0.9999 | 0.14% | `lung_width_asymmetry` 1.06% | 0.1% – 70.9% |
| chexpert | 187825 | 1.0000 | 0.12% | `lung_width_asymmetry` 1.49% | 0.0% – 102.4% |
| mimic | 243334 | 0.9977 | 0.12% | `lung_width_asymmetry` 1.31% | 1.8% – 100.8% |
| padchest | 96184 | 0.9997 | 0.13% | `lung_width_asymmetry` 0.82% | 0.5% – 42.5% |

**Verdict.** Every mask-against-mask ratio agrees to within 1.49% on every dataset, so CTR computed from either variant is interchangeable — that is the measure this task asks for. The widest disagreement is `lung_width_asymmetry`, which is a difference of two nearly equal areas divided by their sum, so a small resampling error is amplified; CTR itself stays under 0.2%. Frame-normalised measures (areas and positions as a fraction of the image) do not agree: they move with the padding, by up to 102%. Keep one variant per analysis for those, and prefer `OriginalResolution` when the question is where things sit.

## Full table — vindr

| group | measure | n | pearson r | mean abs rel diff | p99 | mean A | mean B |
|---|---|---:|---:|---:|---:|---:|---:|
| mask-vs-mask ratio (must agree) | `ctr` | 18000 | 0.9999 | 0.14% | 0.40% | 0.4823 | 0.4829 |
| mask-vs-mask ratio (must agree) | `ctr_same_level` | 18000 | 0.9861 | 0.26% | 0.85% | 0.5086 | 0.5054 |
| mask-vs-mask ratio (must agree) | `ctr_bbox` | 18000 | 1.0000 | 0.10% | 0.23% | 0.4938 | 0.4942 |
| mask-vs-mask ratio (must agree) | `heart_lung_area_ratio` | 18000 | 1.0000 | 0.06% | 0.24% | 0.3624 | 0.3622 |
| mask-vs-mask ratio (must agree) | `lung_width_asymmetry` | 18000 | 1.0000 | 1.06% | 3.32% | -0.0931 | -0.0928 |
| frame-normalised (may shift with padding) | `heart_area_frac` | 18000 | 0.9242 | 12.77% | 23.35% | 0.0834 | 0.0727 |
| frame-normalised (may shift with padding) | `left_lung_area_frac` | 18000 | 0.9447 | 12.73% | 23.37% | 0.1086 | 0.0946 |
| frame-normalised (may shift with padding) | `right_lung_area_frac` | 18000 | 0.9428 | 12.77% | 23.35% | 0.1308 | 0.1139 |
| frame-normalised (may shift with padding) | `lung_area_frac` | 18000 | 0.9408 | 12.75% | 23.37% | 0.2393 | 0.2085 |
| frame-normalised (may shift with padding) | `heart_width_norm` | 18000 | 0.8248 | 12.60% | 23.33% | 0.3691 | 0.3218 |
| frame-normalised (may shift with padding) | `thorax_width_norm` | 18000 | 0.7225 | 12.66% | 23.42% | 0.7675 | 0.668 |
| frame-normalised (may shift with padding) | `heart_centroid_x_norm` | 18000 | 0.9828 | 1.34% | 3.79% | 0.5599 | 0.5525 |
| frame-normalised (may shift with padding) | `heart_centroid_y_norm` | 18000 | 0.9991 | 0.06% | 1.82% | 0.5768 | 0.5765 |
| frame-normalised (may shift with padding) | `lung_centroid_x_norm` | 18000 | 0.9958 | 0.65% | 3.80% | 0.4931 | 0.4943 |
| frame-normalised (may shift with padding) | `lung_centroid_y_norm` | 18000 | 0.9995 | 0.09% | 1.63% | 0.4118 | 0.4121 |
| frame-normalised (may shift with padding) | `heart_bbox_left_norm` | 18000 | 0.9619 | 4.45% | 14.66% | 0.3794 | 0.3954 |
| frame-normalised (may shift with padding) | `heart_bbox_top_norm` | 18000 | 0.9995 | 0.07% | 1.61% | 0.4136 | 0.4138 |
| frame-normalised (may shift with padding) | `heart_bbox_right_norm` | 18000 | 0.8914 | 14.76% | 44.34% | 0.2413 | 0.2739 |
| frame-normalised (may shift with padding) | `heart_bbox_bottom_norm` | 18000 | 0.9962 | 0.60% | 12.43% | 0.2845 | 0.2847 |
| frame-normalised (may shift with padding) | `lung_bbox_left_norm` | 18000 | 0.8194 | 70.91% | 434.16% | 0.1142 | 0.1648 |
| frame-normalised (may shift with padding) | `lung_bbox_top_norm` | 18000 | 0.9898 | 1.21% | 31.83% | 0.1342 | 0.1353 |
| frame-normalised (may shift with padding) | `lung_bbox_right_norm` | 18000 | 0.7876 | 58.41% | 289.19% | 0.1156 | 0.1649 |
| frame-normalised (may shift with padding) | `lung_bbox_bottom_norm` | 18000 | 0.9973 | 1.02% | 18.50% | 0.2321 | 0.2324 |
| absolute px (must differ) | `heart_width_px` | 18000 | 0.7603 | 62.75% | 69.87% | 893.7 | 329.546 |
| absolute px (must differ) | `thorax_width_px` | 18000 | 0.6387 | 62.79% | 69.92% | 1856.67 | 684.069 |
| absolute px (must differ) | `heart_area_px` | 18000 | 0.6383 | 85.95% | 90.93% | 566905 | 76233.9 |
| absolute px (must differ) | `lung_area_px` | 18000 | 0.6916 | 85.95% | 90.93% | 1.62349e+06 | 218610 |

## Reproduce

```bash
for ds in vindr chexpert mimic padchest chestxray8; do
  python scripts/compute_anatomical_measures.py --dataset $ds --variant original --n 200
done
for ds in vindr chexpert mimic padchest; do
  python scripts/compute_anatomical_measures.py --dataset $ds --variant preprocessed --n 200
done
python scripts/variant_agreement.py --out output/VARIANT_AGREEMENT.md
```
