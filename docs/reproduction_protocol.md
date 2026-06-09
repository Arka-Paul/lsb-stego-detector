# Reproduction Protocol

This document describes how to reproduce and verify the experimental workflow for the LSB stego detector project.

The repository supports two levels of reproducibility:

1. **Result verification** using the CSV files provided in `results/`.
2. **Full experiment regeneration** using the provided scripts, payloads, manifests, and carrier images where available.

All final reported results are based on the **combined dataset workflow**, not the preliminary small-dataset workflow.

---

## 1. Reproduction Scope

This repository provides the source code, experimental scripts, payload files, manifests, and result CSV files required to verify the reported experimental outputs. The uploaded CSV files in `results/` support verification of the main manuscript tables, including detection accuracy, payload-level attribution, false-positive analysis, ablation testing, robustness/safe-failure analysis, runtime analysis, and baseline comparison.

Full regeneration of the complete stego-image dataset requires the carrier image folders and sufficient local storage. If the complete generated stego-image set is not included in the repository due to repository-size constraints, users can still reproduce the reported tables from the provided manifests and result files, or regenerate the dataset locally after placing the carrier images in the expected directory structure used by the scripts.

---

## 2. Repository Setup

Clone the repository:

```bash
git clone https://github.com/Arka-Paul/lsb-stego-detector.git
cd lsb-stego-detector
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install external forensic tools used for baseline comparison:

```bash
sudo apt update
sudo apt install binwalk foremost exiftool
gem install zsteg
```

The project was developed and tested on Kali Linux. The exact environment used for the reported experiments is documented in:

```text
docs/tool_versions.md
```

---

## 3. Main Repository Components

```text
scripts/                  Python scripts used for detection and evaluation
results/                  CSV files underlying the reported manuscript tables
dataset/sample_payloads/  Payload files used for controlled embedding
docs/                     Reproducibility and environment documentation
```

The final combined experiment uses:

```text
46 cover images
6 payload types
3 payload size classes
3 LSB depths
2484 planned embedding cases
1848 valid generated stego-images
```

The reduction from 2484 planned embedding cases to 1848 valid stego-images is due to:

1. carrier-capacity constraints, where larger payloads exceeded available embedding capacity for some image/depth combinations;
2. a StegoLSB implementation limitation affecting greyscale PNG images.

---

## 4. Result Verification from Existing CSV Files

The following result files are provided in the `results/` directory:

```text
embedding_plan_combined.csv
stego_manifest_combined.csv
detection_results_combined.csv
confusion_matrix.csv
table3_per_payload.csv
table_category_analysis.csv
false_positive_analysis.csv
false_positive_clean_results.csv
ablation_results_summary.csv
ablation_results_per_file.csv
robustness_selected_subset.csv
robustness_results_per_file.csv
robustness_table.csv
runtime_summary.csv
runtime_per_file.csv
```

These files contain the data underlying the reported manuscript tables.

Key reported results are:

```text
Proposed method accuracy: 1848/1848 = 100.00%
False-positive rate: 3/138 = 2.17%
Ablation, full system: 1848/1848 = 100.00%
Ablation, without deinterleaving: 474/1848 = 25.65%
Ablation, reduced buffer: 924/1848 = 50.00%
Ablation, without internal markers: 924/1848 = 50.00%
Average runtime per image: 5.50 seconds
```

---

## 5. Full Combined Workflow

The following commands reproduce the combined experimental workflow when the required carrier images and payload files are available in the expected folder structure.

### Step 1: Build the combined embedding plan

```bash
python3 scripts/build_combined_embedding_plan.py
```

Expected output:

```text
results/embedding_plan_combined.csv
```

This file lists planned embedding attempts, valid embedding configurations, and skipped cases due to carrier-capacity limitations or tool-specific constraints.

---

### Step 2: Generate stego-images

```bash
python3 scripts/run_embedding_combined.py
```

Expected output:

```text
1848 successfully generated stego-images
```

This script embeds payloads into compatible cover images using the planned configurations.

---

### Step 3: Build the stego manifest

```bash
python3 scripts/build_stego_manifest_combined.py
```

Expected output:

```text
results/stego_manifest_combined.csv
```

The manifest records each stego image, cover image, payload type, payload size class, LSB depth, and expected payload label.

---

### Step 4: Run the proposed detector

```bash
python3 scripts/run_detection_combined.py
```

Expected output:

```text
results/detection_results_combined.csv
```

Expected summary:

```text
Total samples : 1848
Correct       : 1848
Incorrect     : 0
Accuracy      : 1.0000
```

---

### Step 5: Generate the confusion matrix

```bash
python3 scripts/make_confusion_matrix.py
```

Expected output:

```text
results/confusion_matrix.csv
```

This file summarises actual versus predicted payload classes for the proposed method.

---

### Step 6: Generate payload-level performance table

```bash
python3 scripts/make_table3_per_payload.py
```

Expected output:

```text
results/table3_per_payload.csv
```

This file summarises attribution accuracy by payload type.

---

### Step 7: Generate image-category performance table

```bash
python3 scripts/make_table_category.py
```

Expected output:

```text
results/table_category_analysis.csv
```

This file summarises performance across the controlled image categories.

---

### Step 8: Run false-positive analysis

```bash
python3 scripts/run_false_positive_clean.py
```

Expected outputs:

```text
results/false_positive_clean_results.csv
results/false_positive_analysis.csv
```

Expected summary:

```text
46 clean images tested across 3 LSB depths
138 total clean-image test cases
3 false-positive events
2.17% overall false-positive rate
```

---

### Step 9: Run ablation study

```bash
python3 scripts/run_ablation_study.py
```

Expected outputs:

```text
results/ablation_results_per_file.csv
results/ablation_results_summary.csv
```

Expected summary:

```text
full: 1848/1848 = 100.00%
no_deinterleaving: 474/1848 = 25.65%
no_buffer: 924/1848 = 50.00%
no_markers: 924/1848 = 50.00%
```

---

### Step 10: Run robustness / safe-failure analysis

```bash
python3 scripts/run_robustness_analysis.py
```

Expected outputs:

```text
results/robustness_selected_subset.csv
results/robustness_results_per_file.csv
results/robustness_table.csv
```

Expected scenarios:

```text
Original
Reduced Buffer
JPEG Compression
Resizing
Slight Noise
Wrong LSB Depth
```

The transformation-based scenarios are expected to fail safely by returning `UNKNOWN`, because the LSB payload structure is disrupted by changes to pixel values or extraction parameters.

---

### Step 11: Run runtime analysis

```bash
python3 scripts/run_runtime_analysis.py
```

Expected outputs:

```text
results/runtime_per_file.csv
results/runtime_summary.csv
```

Expected summary:

```text
Total images processed: 1848
Correct detections: 1848
Average runtime per image: approximately 5.50 seconds
```

Runtime values may vary depending on hardware, storage speed, Python environment, and available system resources.

---

### Step 12: Run baseline tool comparison

```bash
python3 scripts/compare_baseline_tools_combined.py
```

Expected outputs:

```text
results/tool_comparison_per_file.csv
results/tool_comparison_summary.csv
```

This script compares the proposed detector against:

```text
zsteg
binwalk
foremost
exiftool
```

These tools are included as baseline forensic utilities with different operating assumptions. `binwalk`, `foremost`, and `exiftool` do not reconstruct LSB bitstreams before analysis, so their results should be interpreted as traditional raw-byte or metadata-level baselines rather than direct equivalents to the proposed reconstruction method.

---

## 6. Command-Line Detector Test

The detector can be tested on a single stego image using:

```bash
python3 scripts/detector_cli.py <image_path> <lsb_depth>
```

Example:

```bash
python3 scripts/detector_cli.py stego_core_combined/Flat-Color_1_S__pdf_small__lsb1.bmp 1
```

Expected output:

```text
PDF
```

The command-line detector returns one of:

```text
PDF, DOCX, XLSX, PPTX, RTF, EXE, ZIP, UNKNOWN, ERROR
```

---

## 7. Interpretation of Results

All reported results are limited to controlled StegoLSB-compatible sequential embedding conditions.

The proposed method is not a universal detector for all steganography methods. It is designed to reconstruct and attribute payloads under a compatible sequential LSB embedding model.

Failure under JPEG compression, resizing, additive noise, incorrect LSB depth, or insufficient buffer extraction should be interpreted as safe failure under the tested perturbations, not broad robustness against transformed or adversarial stego-images.

---

## 8. Notes on Greyscale PNG Handling

A StegoLSB implementation limitation was observed for greyscale PNG images. In RGB images, pixels are represented as channel tuples, whereas in greyscale PNG images, pixels may be represented as scalar intensity values. Some embedding routines assume iterable pixel-channel structures and may fail on scalar greyscale pixels.

This limitation affects dataset generation for greyscale PNG carriers. It is a tool-specific implementation constraint rather than a limitation of the proposed reconstruction logic.

---

## 9. Notes on Storage and Temporary Files

Full regeneration of the dataset can require substantial local disk space because large stego-images and temporary output folders may be created. This is especially relevant for scripts involving XL carriers and `foremost` comparison outputs.

Before running full regeneration, ensure that sufficient disk space is available. Temporary output folders should not be committed to the repository.

---

## 10. Expected Output Files

After running the complete workflow, the main output files should include:

```text
results/embedding_plan_combined.csv
results/stego_manifest_combined.csv
results/detection_results_combined.csv
results/confusion_matrix.csv
results/table3_per_payload.csv
results/table_category_analysis.csv
results/false_positive_clean_results.csv
results/false_positive_analysis.csv
results/ablation_results_per_file.csv
results/ablation_results_summary.csv
results/robustness_selected_subset.csv
results/robustness_results_per_file.csv
results/robustness_table.csv
results/runtime_per_file.csv
results/runtime_summary.csv
results/tool_comparison_per_file.csv
results/tool_comparison_summary.csv
```

These files provide the data required to reproduce or verify the quantitative results reported in the manuscript.
