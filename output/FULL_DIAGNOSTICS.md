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

| dataset | r(CTR, image width) | r(CTR, lung area) | r(thorax width, lung area) | r(heart width, lung area) | partial r(CTR, lung area \| thorax width) | lung touches border |
|---|---:|---:|---:|---:|---:|---:|
| chestxray8 | — | -0.574 | +0.597 | -0.119 | -0.489 | 3.9% |
| chexpert | +0.144 | -0.482 | +0.548 | -0.076 | -0.431 | 4.2% |
| mimic | +0.080 | -0.606 | +0.547 | -0.195 | -0.546 | 4.1% |
| padchest | +0.097 | -0.567 | +0.575 | -0.075 | -0.569 | 0.9% |
| vindr | +0.058 | -0.579 | +0.669 | +0.077 | -0.593 | 0.2% |

Read the first column as a warning: `r(CTR, image width)` is weak (+0.06 … +0.14),
so detector size is not what ranks the datasets — an anatomy-only difference is not
explained away as magnification.

The last-but-one column is the substance. CTR and lung area are coupled (-0.48 …
-0.61), and part of that is arithmetic: the thorax width sits in the CTR denominator
and moves with lung area (+0.55 … +0.67). But it is not only arithmetic. Controlling
for thorax width leaves a partial correlation of -0.43 … -0.59, and the heart width
itself is nearly uncorrelated with lung area (-0.20 … +0.08). So the coupling runs
through how tall and expanded the lungs are, and how the film was framed, rather than
through the heart: inspiration, positioning or habitus. Which of those it is cannot
be read off these tables; acquisition metadata and demographics can.

