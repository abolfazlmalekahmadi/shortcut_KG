# What the anatomical measures say — `original` grids

Distributions and data quality are computed over all rows; means, effect sizes and
correlations over the `quality_ok` rows (Dice RCA mean >= 0.7). Effect sizes `d` are
relative to `vindr`: how many within-sample standard deviations apart the two
dataset means are.

## Data quality and the CTR distribution

| dataset | rows | quality-fail | empty organ | CTR undefined | CTR p10 | CTR median | CTR p90 | CTR > 0.5 | CTR > 0.6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| chestxray8 | 112,120 | 1.18% | 0 | 0 | 0.398 | 0.466 | 0.552 | 29.7% | 2.8% |
| chexpert | 187,825 | 0.55% | 0 | 0 | 0.428 | 0.502 | 0.581 | 51.5% | 5.6% |
| mimic | 243,334 | 2.40% | 49 | 49 | 0.423 | 0.508 | 0.596 | 54.5% | 9.0% |
| padchest | 96,184 | 1.31% | 1 | 0 | 0.389 | 0.454 | 0.541 | 22.9% | 2.1% |
| vindr | 18,000 | 0.47% | 0 | 0 | 0.418 | 0.477 | 0.549 | 33.0% | 2.1% |

## How far apart the datasets are

| dataset | images | CTR | d(CTR) | heart/lung area | d(h/l area) | lung area | d(lung area) | median size | distinct sizes |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| chestxray8 | 110,795 | 0.471 ± 0.061 | -0.17 | 0.381 ± 0.118 | +0.18 | 0.245 ± 0.056 | +0.09 | 1024x1024 | 1 |
| chexpert | 186,791 | 0.504 ± 0.059 | +0.38 | 0.438 ± 0.122 | +0.66 | 0.245 ± 0.049 | +0.10 | 2828x2320 | 6978 |
| mimic | 237,498 | 0.509 ± 0.067 | +0.42 | 0.455 ± 0.145 | +0.67 | 0.238 ± 0.056 | -0.04 | 2544x2734 | 16656 |
| padchest | 94,927 | 0.460 ± 0.060 | -0.36 | 0.365 ± 0.104 | +0.06 | 0.259 ± 0.056 | +0.34 | 2000x1884 | 33383 |
| vindr | 17,915 | 0.481 ± 0.052 | +0.00 | 0.360 ± 0.091 | +0.00 | 0.240 ± 0.053 | +0.00 | 2361x2836 | 6486 |

`lung area` is the fraction of the image the two lungs occupy, so it is also a
statement about how much of the frame the segmentation fills (collimation, crop,
positioning).

## Is the gap confounded with acquisition geometry?

| dataset | r(CTR, width) | r(CTR, height) | r(CTR, aspect) | r(CTR, lung area) | lung touches border |
|---|---:|---:|---:|---:|---:|
| chestxray8 | — | — | — | -0.574 | 3.9% |
| chexpert | +0.144 | +0.115 | +0.148 | -0.482 | 4.2% |
| mimic | +0.080 | +0.066 | +0.016 | -0.606 | 4.1% |
| padchest | +0.097 | +0.066 | +0.138 | -0.567 | 0.9% |
| vindr | +0.058 | +0.017 | +0.084 | -0.579 | 0.2% |

Read these correlations as a warning, not a mechanism: a strong `r(CTR, size)` would
say the dataset ranking partly reflects detector size or processing rather than the
population. Only acquisition metadata and demographics can settle it.

