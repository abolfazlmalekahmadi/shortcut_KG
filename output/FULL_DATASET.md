| dataset | variant | n | ok | CTR | heart w | thorax w | lung area | heart/lung area |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| chestxray8 | original | 112120 | 110795 | 0.471 ± 0.061 | 355.6 ± 46.6 | 757.6 ± 73.8 | 24.5% | 0.381 ± 0.118 |
| chexpert | original | 187825 | 186791 | 0.504 ± 0.059 | 997.6 ± 190.4 | 1,980 ± 298.1 | 24.5% | 0.438 ± 0.122 |
| chexpert | preprocessed | 187825 | 186791 | 0.504 ± 0.059 | 371.7 ± 47.6 | 739.0 ± 64.0 | 20.7% | 0.438 ± 0.122 |
| mimic | original | 243334 | 237498 | 0.509 ± 0.067 | 1,029 ± 185.8 | 2,025 ± 294.6 | 23.8% | 0.455 ± 0.145 |
| mimic | preprocessed | 243334 | 237498 | 0.510 ± 0.067 | 378.0 ± 54.0 | 744.2 ± 73.1 | 21.4% | 0.455 ± 0.145 |
| padchest | original | 96184 | 94927 | 0.460 ± 0.060 | 809.6 ± 298.0 | 1,758 ± 589.5 | 25.9% | 0.365 ± 0.104 |
| padchest | preprocessed | 96184 | 94927 | 0.460 ± 0.060 | 351.2 ± 50.8 | 764.7 ± 72.5 | 24.1% | 0.365 ± 0.103 |
| vindr | original | 18000 | 17915 | 0.481 ± 0.052 | 892.2 ± 145.5 | 1,858 ± 255.8 | 24.0% | 0.360 ± 0.091 |
| vindr | preprocessed | 18000 | 17915 | 0.482 ± 0.052 | 329.1 ± 46.3 | 684.6 ± 74.6 | 20.9% | 0.359 ± 0.091 |

Statistics are computed on `quality_ok` rows only (`Dice RCA (Mean) >= 0.7`). `n` is every row read, `ok` the passing ones. Pixel widths are not comparable across datasets.
