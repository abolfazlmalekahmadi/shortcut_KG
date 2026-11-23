# OriginalResolution vs Preprocessed — do the measures agree?

Same code, same images, two published rasters. `mean abs rel diff` is the mean of `|B - A| / A` over the images the two runs share, so `0.2%` means the two grids give, on average, a value 0.2% away from each other.

| dataset | images | CTR r | CTR mean abs rel diff | worst mask-vs-mask ratio | frame-normalised drift |
|---|---:|---:|---:|---|---|
| vindr | 200 | 0.9999 | 0.14% | `lung_width_asymmetry` 0.36% | 0.1% – 66.5% |
| chexpert | 200 | 1.0000 | 0.12% | `lung_width_asymmetry` 0.87% | 0.0% – 99.4% |
| mimic | 200 | 0.9999 | 0.12% | `lung_width_asymmetry` 0.54% | 1.5% – 99.1% |
| padchest | 200 | 1.0000 | 0.13% | `lung_width_asymmetry` 3.58% | 0.6% – 37.7% |

**Verdict.** Every mask-against-mask ratio agrees to within 3.58% on every dataset, so CTR computed from either variant is interchangeable — that is the measure this task asks for. The widest disagreement is `lung_width_asymmetry`, which is a difference of two nearly equal areas divided by their sum, so a small resampling error is amplified; CTR itself stays under 0.2%. Frame-normalised measures (areas and positions as a fraction of the image) do not agree: they move with the padding, by up to 99%. Keep one variant per analysis for those, and prefer `OriginalResolution` when the question is where things sit.

## Full table — vindr

| group | measure | n | pearson r | mean abs rel diff | p99 | mean A | mean B |
|---|---|---:|---:|---:|---:|---:|---:|
| mask-vs-mask ratio (must agree) | `ctr` | 200 | 0.9999 | 0.14% | 0.35% | 0.4882 | 0.4888 |
| mask-vs-mask ratio (must agree) | `ctr_same_level` | 200 | 0.9999 | 0.20% | 0.75% | 0.5015 | 0.5024 |
| mask-vs-mask ratio (must agree) | `ctr_bbox` | 200 | 1.0000 | 0.09% | 0.21% | 0.5003 | 0.5008 |
| mask-vs-mask ratio (must agree) | `heart_lung_area_ratio` | 200 | 1.0000 | 0.06% | 0.21% | 0.3721 | 0.3719 |
| mask-vs-mask ratio (must agree) | `lung_width_asymmetry` | 200 | 1.0000 | 0.36% | 1.39% | -0.087 | -0.0867 |
| frame-normalised (may shift with padding) | `heart_area_frac` | 200 | 0.8971 | 12.83% | 24.41% | 0.0835 | 0.0728 |
| frame-normalised (may shift with padding) | `left_lung_area_frac` | 200 | 0.9417 | 12.79% | 24.35% | 0.1069 | 0.093 |
| frame-normalised (may shift with padding) | `right_lung_area_frac` | 200 | 0.9412 | 12.82% | 24.39% | 0.1273 | 0.1107 |
| frame-normalised (may shift with padding) | `lung_area_frac` | 200 | 0.9391 | 12.81% | 24.37% | 0.2342 | 0.2037 |
| frame-normalised (may shift with padding) | `heart_width_norm` | 200 | 0.7875 | 12.56% | 24.62% | 0.3723 | 0.3249 |
| frame-normalised (may shift with padding) | `thorax_width_norm` | 200 | 0.6740 | 12.64% | 24.66% | 0.7652 | 0.6659 |
| frame-normalised (may shift with padding) | `heart_centroid_x_norm` | 200 | 0.9822 | 1.32% | 4.00% | 0.5592 | 0.5518 |
| frame-normalised (may shift with padding) | `heart_centroid_y_norm` | 200 | 0.9994 | 0.05% | 2.06% | 0.5701 | 0.5698 |
| frame-normalised (may shift with padding) | `lung_centroid_x_norm` | 200 | 0.9953 | 0.67% | 4.59% | 0.4939 | 0.4951 |
| frame-normalised (may shift with padding) | `lung_centroid_y_norm` | 200 | 0.9986 | 0.15% | 5.28% | 0.4051 | 0.4056 |
| frame-normalised (may shift with padding) | `heart_bbox_left_norm` | 200 | 0.9552 | 4.53% | 13.32% | 0.3769 | 0.3931 |
| frame-normalised (may shift with padding) | `heart_bbox_top_norm` | 200 | 0.9992 | 0.11% | 3.59% | 0.4068 | 0.4072 |
| frame-normalised (may shift with padding) | `heart_bbox_right_norm` | 200 | 0.8752 | 14.85% | 43.23% | 0.24 | 0.2728 |
| frame-normalised (may shift with padding) | `heart_bbox_bottom_norm` | 200 | 0.9956 | 0.53% | 15.32% | 0.2912 | 0.2914 |
| frame-normalised (may shift with padding) | `lung_bbox_left_norm` | 200 | 0.7977 | 66.53% | 542.52% | 0.1158 | 0.1663 |
| frame-normalised (may shift with padding) | `lung_bbox_top_norm` | 200 | 0.9842 | 1.58% | 50.20% | 0.1321 | 0.1335 |
| frame-normalised (may shift with padding) | `lung_bbox_right_norm` | 200 | 0.7567 | 59.67% | 283.45% | 0.1162 | 0.1655 |
| frame-normalised (may shift with padding) | `lung_bbox_bottom_norm` | 200 | 0.9976 | 0.64% | 13.77% | 0.2451 | 0.2453 |
| frame-normalised (may shift with padding) | `image_aspect` | 200 | — | 15.73% | 32.82% | 0.8775 | 1 |
| absolute px (must differ) | `heart_width_px` | 200 | 0.7395 | 62.95% | 69.87% | 907.77 | 332.68 |
| absolute px (must differ) | `thorax_width_px` | 200 | 0.6157 | 63.00% | 69.94% | 1862.67 | 681.915 |
| absolute px (must differ) | `heart_area_px` | 200 | 0.6065 | 86.11% | 90.93% | 574642 | 76342.4 |
| absolute px (must differ) | `lung_area_px` | 200 | 0.7207 | 86.10% | 90.93% | 1.60912e+06 | 213619 |

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
