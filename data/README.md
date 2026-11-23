# CheXmask Database v1.0.1

A comprehensive collection of anatomical segmentation masks for chest radiographs derived from five major public databases.

## Overview

The CheXmask Database provides 657,566 anatomical segmentation masks generated from chest radiographs across multiple public databases:
- ChestX-ray8
- Chexpert
- MIMIC-CXR-JPG
- Padchest
- VinDr-CXR

All segmentation masks were generated using the HybridGNet model and include quality metrics based on Reverse Classification Accuracy (RCA) scores.

## Dataset Structure

The dataset consists of CSV files for each source database. Each CSV contains:

| Column Name | Description |
|------------|-------------|
| Image ID | Reference to original image in source dataset |
| Dice RCA (Max) | Maximum Dice Similarity Coefficient for RCA |
| Dice RCA (Mean) | Mean Dice Similarity Coefficient for RCA |
| Landmarks | Organ contour points from HybridGNet model |
| Left Lung | Left lung segmentation mask in RLE format |
| Right Lung | Right lung segmentation mask in RLE format |
| Heart | Heart segmentation mask in RLE format |
| Height | Height of segmentation mask |
| Width | Width of segmentation mask |

## Data Processing

All images were processed to maintain consistent quality:
1. Images were preprocessed to 1024x1024 resolution
2. HybridGNet model was applied for segmentation
3. Masks were restored to original image dimensions
4. RCA scores were calculated for quality assessment

## Usage Guidelines

1. **Source Images**: Users must obtain source images from original databases and comply with their respective requirements (ethics courses, training, etc.).
2. **Quality Threshold**: For analysis, use only segmentation masks with Dice RCA (Mean) >= 0.7
3. **Resolution**: Pre-processed versions (1024x1024) of masks are included for consistent resolution across datasets

## Version History

### v1.0.0
- Updated citation
- Added README file
- Added Data Dictionary

## Citation

When using this dataset, please cite:
Gaggion, N., Mosquera, C., Mansilla, L. et al. CheXmask: a large-scale dataset of anatomical segmentation masks for multi-center chest x-ray images. Sci Data 11, 511 (2024). https://doi.org/10.1038/s41597-024-03358-1
