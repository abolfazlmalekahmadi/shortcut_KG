| dataset | variant | n | ok | CTR | heart w | thorax w | lung area | heart/lung area |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| chestxray8 | original | 200 | 198 | 0.467 ± 0.058 | 349.4 ± 43.8 | 751.5 ± 68.4 | 24.0% | 0.374 ± 0.115 |
| chexpert | original | 200 | 200 | 0.498 ± 0.054 | 980.2 ± 168.3 | 1,970 ± 282.0 | 25.4% | 0.410 ± 0.104 |
| chexpert | preprocessed | 200 | 200 | 0.498 ± 0.054 | 366.5 ± 41.1 | 737.2 ± 59.3 | 21.6% | 0.410 ± 0.104 |
| mimic | original | 200 | 194 | 0.509 ± 0.059 | 1,038 ± 171.4 | 2,046 ± 302.7 | 23.7% | 0.442 ± 0.133 |
| mimic | preprocessed | 200 | 194 | 0.510 ± 0.059 | 377.9 ± 48.6 | 744.2 ± 75.8 | 21.2% | 0.442 ± 0.132 |
| padchest | original | 200 | 198 | 0.455 ± 0.061 | 791.0 ± 304.8 | 1,727 ± 575.5 | 26.1% | 0.358 ± 0.102 |
| padchest | preprocessed | 200 | 198 | 0.455 ± 0.061 | 348.0 ± 51.5 | 765.9 ± 74.6 | 24.4% | 0.358 ± 0.101 |
| vindr | original | 200 | 199 | 0.487 ± 0.051 | 906.3 ± 147.1 | 1,863 ± 256.5 | 23.5% | 0.370 ± 0.096 |
| vindr | preprocessed | 200 | 199 | 0.488 ± 0.051 | 332.3 ± 44.5 | 682.4 ± 69.6 | 20.4% | 0.369 ± 0.096 |

Statistics are computed on `quality_ok` rows only (`Dice RCA (Mean) >= 0.7`). `n` is every row read, `ok` the passing ones. Pixel widths are not comparable across datasets.
