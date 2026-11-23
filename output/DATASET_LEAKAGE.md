# How much of the centre is in the anatomy?

Cross-validated AUC of telling two datasets apart from the anatomy alone — no
image, no model beyond a logistic regression, no metadata. Columns differ only in
which of the 17 measures they may use; `original` grids,
20,000 random quality-ok images per dataset, 5-fold
stratified CV.

| pair | all | frame-invariant | ctr only |
|---|---|---|---|
| mimic vs chexpert | 0.886 | 0.579 | 0.520 |
| mimic vs chestxray8 | 0.769 | 0.671 | 0.664 |
| mimic vs padchest | 0.834 | 0.715 | 0.711 |
| chexpert vs chestxray8 | 0.963 | 0.663 | 0.657 |
| chexpert vs padchest | 0.880 | 0.722 | 0.708 |
| chestxray8 vs padchest | 0.811 | 0.573 | 0.556 |

`frame-invariant` uses only ratios of a mask against itself, so it survives any
rescaling and any change of frame: a dataset named from those alone is named by
its anatomy rather than by its file format. `all` additionally uses the frame,
which is where ChestX-Ray8's 1024x1024 padding gives itself away.

AUC near 0.5 means the anatomy does not know the dataset, near 1.0 that it does.
This is a centre-level signal sitting in measurements that need no image and no
model, so any label correlated with the centre inherits it. It is not by itself
evidence of an artifact: age, sex and disease mix differ between these datasets and
would legitimately move heart size. Separating those needs the acquisition and
demographic columns, which is the next step of E1.
