# LSB Stego Detector: Bitstream Reconstruction for File-Type Attribution

This repository contains the source code, experimental scripts, payload files, result outputs, and reproducibility documentation for the project:

**Decoding Hidden Structures: Bitstream Reconstruction for File-Type Attribution in LSB Steganography**

The project implements a deterministic reconstruction-based forensic pipeline for identifying concealed file types embedded in images using Least Significant Bit (LSB) steganography. Unlike conventional forensic tools that inspect the image file as a contiguous byte stream, this method reconstructs the hidden LSB bitstream first and then applies structurally validated file-type attribution. The updated attribution stage checks both primary file signatures and format-specific structure, including PDF trailer markers, ZIP/Office Open XML structure for DOCX/XLSX/PPTX, RTF control structure, and PE header validation for EXE files.

The repository supports verification and reproduction of the reported experiments, including detection accuracy, payload-level attribution, expanded false-positive analysis, structural-validation testing, ablation testing, robustness/safe-failure analysis, runtime analysis, and comparison against existing forensic tools.

---

## 1. Scope of the Method

The proposed detector is designed for **controlled StegoLSB-compatible sequential embedding conditions**.

The method assumes:

* lossless image carriers, primarily PNG and BMP;
* sequential LSB embedding;
* known or user-specified LSB depth;
* payloads embedded without encryption or pre-embedding obfuscation;
* no destructive post-processing such as JPEG compression, resizing, or additive noise.

The method should therefore be interpreted as a **forensic file-type attribution framework under a compatible embedding model**, not as a universal steganography detector.

The current framework does not claim to recover payloads embedded using randomised traversal, encrypted payloads, compressed payloads, unknown offsets, adaptive embedding, transform-domain steganography, or lossy JPEG-domain embedding. These cases require additional reconstruction, traversal-inference, decryption/decompression, or tool-specific extraction modules.

---

## 2. Repository Structure

```text
lsb-stego-detector/
├── dataset/
│   ├── sample_covers/
│   ├── sample_payloads/
│   │   ├── docx/
│   │   ├── exe/
│   │   ├── pdf/
│   │   ├── pptx/
│   │   ├── rtf/
│   │   └── xlsx/
│   └── sample_stego/
│
├── docs/
│   ├── reproduction_protocol.md
│   └── tool_versions.md
│
├── manifests/
│   └── expanded_clean_manifest.csv
│
├── results/
│   ├── ablation_results_per_file.csv
│   ├── ablation_results_summary.csv
│   ├── confusion_matrix.csv
│   ├── cover_capacity_audit.csv
│   ├── covers_metadata.csv
│   ├── detection_results_combined.csv
│   ├── embedding_plan_combined.csv
│   ├── expanded_clean_false_positive_results.csv
│   ├── false_positive_analysis.csv
│   ├── false_positive_clean_results.csv
│   ├── payload_validation.txt
│   ├── robustness_results_per_file.csv
│   ├── robustness_selected_subset.csv
│   ├── robustness_table.csv
│   ├── runtime_per_file.csv
│   ├── runtime_summary.csv
│   ├── stego_manifest_combined.csv
│   ├── structural_validation_run.log
│   ├── structural_validation_stego_1848.csv
│   ├── structural_validation_summary.csv
│   ├── table3_per_payload.csv
│   ├── table_category_analysis.csv
│   ├── tool_comparison_per_file.csv
│   └── tool_comparison_summary.csv
│
├── scripts/
│   ├── build_combined_embedding_plan.py
│   ├── build_stego_manifest_combined.py
│   ├── compare_baseline_tools_combined.py
│   ├── detector_ablation.py
│   ├── detector_cli.py
│   ├── main.py
│   ├── make_confusion_matrix.py
│   ├── make_false_positive_table.py
│   ├── make_table3_per_payload.py
│   ├── make_table_category.py
│   ├── run_ablation_study.py
│   ├── run_detection_combined.py
│   ├── run_embedding_combined.py
│   ├── run_false_positive_clean.py
│   ├── run_robustness_analysis.py
│   ├── run_runtime_analysis.py
│   ├── run_structural_validation_1848.py
│   └── updated_main.py
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 3. Dataset and Payload Composition

The reported evaluation uses a controlled combined dataset generated from:

* **46 cover images**

  * 16 controlled core images;
  * 30 extended XL synthetic images.

* **6 payload types**

  * PDF;
  * DOCX;
  * XLSX;
  * PPTX;
  * RTF;
  * EXE.

* **3 payload size classes**

  * small;
  * medium;
  * large.

* **3 LSB embedding depths**

  * 1-bit;
  * 2-bit;
  * 3-bit.

Under ideal execution conditions, the full planned embedding space is:

```text
46 covers × 6 payload types × 3 payload sizes × 3 LSB depths = 2484 planned cases
```

The final valid stego dataset contains:

```text
1848 valid stego-images
```

The reduction from 2484 planned cases to 1848 valid cases is due to:

1. carrier-capacity limitations, where larger payloads exceeded available embedding capacity for some image/depth combinations;
2. a StegoLSB implementation limitation affecting greyscale PNG images, where scalar pixel representation can cause embedding failure.

Only successfully generated stego-images were included in the final evaluation.

The clean-image false-positive evaluation contains:

```text
Original controlled clean images: 46
Original clean-image test cases: 46 × 3 LSB depths = 138

Expanded independent clean images: 200
Expanded clean-image test cases: 200 × 3 LSB depths = 600

Combined clean-image test cases: 738
```

The expanded clean-image set contains:

```text
Camera/natural photographs: 50 images
Screenshots: 50 images
Scanned document-page images: 50 images
Noisy images: 50 images
```

The original controlled clean set already included additional visual categories such as flat-colour, greyscale, high-detail, low-detail, mixed-content, noisy, photographic, and transparency-based images.

---

## 4. Repository Data Availability

This GitHub repository contains:

* source code used for detection and evaluation;
* structurally validated detector scripts;
* payload files used for controlled embedding experiments;
* result CSV files underlying the reported manuscript tables;
* sample cover images;
* sample stego-images;
* reproducibility documentation;
* tool and environment version documentation.

The repository currently includes a sample image subset for demonstration and testing. The complete generated stego-image dataset is not stored directly in the GitHub repository due to repository-size considerations. The full stego-image dataset can be regenerated using the provided payloads, scripts, manifests, and carrier image configuration when the full carrier image set is placed in the expected directory structure.

The expanded clean-image false-positive evaluation contains 200 additional clean images. The public release includes the non-sensitive portions of this evaluation, aggregate result CSV files, metadata, and reproducibility scripts. The 50 camera/natural photograph images used in the expanded clean-image evaluation are not publicly released because they may contain identifiable individuals or private visual information. These images were used only for aggregate false-positive testing and were not used for stego-image generation, training, or method tuning.

No personal data are included in the public release.

Where a separate external dataset archive is available, the corresponding DOI or repository link should be cited in the manuscript Data Availability Statement.

---

## 5. Payload Files

The folder `dataset/sample_payloads/` contains the benign synthetic payload files used in the experiments. Payloads are organised by file type and size class.

The EXE files are included only as harmless test binaries for signature-based attribution experiments. They are not malware.

The EXE payload SHA-256 hashes are:

```text
medium/P06.exe:
8dbba6af13993a1c9eb868ded6a68101c036f025aefe055ac98932ebe6233366

large/P06.exe:
68dce1774763ef5c2ed853d26b6d0a9d1f9e70cb83f08b7e5c28069aa0b92bb3

small/P06.exe:
e99c275bc74742ccaf781942ee66a06e6da063ceacb9165d61ee67fc84b3558d
```

---

## 6. Proposed Detector

The detector is provided in GUI and command-line/scripted forms.

### GUI version

```text
scripts/main.py
scripts/updated_main.py
```

The updated GUI version includes structurally validated attribution. It allows users to select PNG/BMP images, specify candidate LSB depths, and view the detected file type and reconstructed header evidence.

### Command-line version

```text
scripts/detector_cli.py
```

Example usage:

```bash
python3 scripts/detector_cli.py <image_path> <lsb_depth>
```

Example:

```bash
python3 scripts/detector_cli.py dataset/sample_stego/<sample_stego_image>.bmp 1
```

### Structural-validation batch script

```text
scripts/run_structural_validation_1848.py
```

This script re-evaluates the full stego-image dataset using the structurally validated attribution rule and writes detailed CSV outputs.

Example:

```bash
python3 -u scripts/run_structural_validation_1848.py \
  --input-root ./stego_core_combined \
  --out-csv ./results/structural_validation_stego_1848.csv \
  --summary-csv ./results/structural_validation_summary.csv
```

The detector workflow:

1. opens the input image;
2. flattens pixel/channel values;
3. reconstructs LSB bitstreams using StegoLSB-compatible deinterleaving;
4. removes the StegoLSB length-tag prefix;
5. reconstructs candidate payload bytes;
6. checks primary file signatures;
7. applies structural validation:

   * PDF: `%PDF` header, `startxref`, and `%%EOF`;
   * DOCX/XLSX/PPTX: valid ZIP/OOXML structure, `[Content_Types].xml`, and subtype markers such as `word/`, `xl/`, or `ppt/`;
   * EXE: `MZ` header and valid `PE\x00\x00` header at the `e_lfanew` offset;
   * RTF: `{\rtf1` header and basic RTF control structure;

8. returns one of:

```text
PDF, DOCX, XLSX, PPTX, RTF, EXE, Unknown/None, Processing Failed
```

---

## 7. Installation

The code was developed and tested using Python 3 on Kali Linux.

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

The following external forensic tools were used for comparison experiments:

```text
zsteg
binwalk
foremost
exiftool
```

On Kali Linux, they can typically be installed using:

```bash
sudo apt update
sudo apt install binwalk foremost exiftool
gem install zsteg
```

The exact versions used in the reported experiments are documented in:

```text
docs/tool_versions.md
```

---

## 8. Reproducing the Main Results

The final results reported in the manuscript are based on the combined dataset workflow. A more detailed protocol is available in:

```text
docs/reproduction_protocol.md
```

### Step 1: Build the combined embedding plan

```bash
python3 scripts/build_combined_embedding_plan.py
```

This generates:

```text
results/embedding_plan_combined.csv
```

### Step 2: Generate stego-images

```bash
python3 scripts/run_embedding_combined.py
```

This embeds the payload files into compatible cover images using the planned configurations.

### Step 3: Build the stego manifest

```bash
python3 scripts/build_stego_manifest_combined.py
```

This generates:

```text
results/stego_manifest_combined.csv
```

### Step 4: Run the proposed detector

```bash
python3 scripts/run_detection_combined.py
```

This generates:

```text
results/detection_results_combined.csv
```

### Step 5: Generate confusion matrix

```bash
python3 scripts/make_confusion_matrix.py
```

This generates:

```text
results/confusion_matrix.csv
```

### Step 6: Run false-positive analysis on clean images

```bash
python3 scripts/run_false_positive_clean.py
```

This generates:

```text
results/false_positive_clean_results.csv
results/false_positive_analysis.csv
```

### Step 6b: Run structurally validated stego-image verification

```bash
python3 -u scripts/run_structural_validation_1848.py \
  --input-root ./stego_core_combined \
  --out-csv ./results/structural_validation_stego_1848.csv \
  --summary-csv ./results/structural_validation_summary.csv \
  | tee ./results/structural_validation_run.log
```

This generates:

```text
results/structural_validation_stego_1848.csv
results/structural_validation_summary.csv
results/structural_validation_run.log
```

The structurally validated detector retained correct attribution on all 1,848 valid stego-images at the expected embedding depth.

### Step 6c: Run expanded clean-image false-positive evaluation

The expanded clean-image evaluation tests 200 additional clean images across three assumed LSB depths, producing 600 additional clean-image test cases.

Expected output files:

```text
manifests/expanded_clean_manifest.csv
results/expanded_clean_false_positive_results.csv
```

The private camera/natural photograph subset is not publicly released. Aggregate results and metadata are provided for reproducibility without exposing private visual content.

### Step 7: Run ablation study

```bash
python3 scripts/run_ablation_study.py
```

This generates:

```text
results/ablation_results_per_file.csv
results/ablation_results_summary.csv
```

### Step 8: Run robustness / safe-failure analysis

```bash
python3 scripts/run_robustness_analysis.py
```

This generates:

```text
results/robustness_results_per_file.csv
results/robustness_selected_subset.csv
results/robustness_table.csv
```

### Step 9: Run runtime analysis

```bash
python3 scripts/run_runtime_analysis.py
```

This generates:

```text
results/runtime_per_file.csv
results/runtime_summary.csv
```

### Step 10: Run baseline tool comparison

```bash
python3 scripts/compare_baseline_tools_combined.py
```

This compares the proposed method against:

```text
zsteg
binwalk
foremost
exiftool
```

Expected output files:

```text
results/tool_comparison_per_file.csv
results/tool_comparison_summary.csv
```

If these files are not present in the repository, they can be regenerated using the command above when the required stego-image dataset is available locally.

---

## 9. Summary of Main Experimental Results

### Proposed method

```text
Total valid stego samples: 1848
Correct attributions: 1848
Accuracy: 100.00%
Exact 95% binomial confidence interval: 99.80%--100.00%
```

### Structurally validated attribution

```text
Valid stego-images tested at expected embedding depth: 1848
Correct structurally validated attributions: 1848
Failed expected-depth attributions: 0
Processing errors: 0
Expected-depth accuracy: 100.00%
```

Structural validation reduced accidental clean-image matches while preserving attribution accuracy on the valid stego-image dataset.

### Payload-level performance

```text
PDF:  308/308
DOCX: 308/308
XLSX: 308/308
PPTX: 308/308
RTF:  308/308
EXE:  308/308
```

### Embedding-depth performance

```text
1-bit LSB: 474 samples, 100.00%
2-bit LSB: 624 samples, 100.00%
3-bit LSB: 750 samples, 100.00%
```

### Clean-image false-positive analysis

The initial signature-based attribution rule produced three false positives on the original clean-image evaluation:

```text
Original clean images: 46
LSB depths tested: 3
Original clean-image test cases: 138
False-positive events under initial signature-only rule: 3
Initial false-positive rate: 2.17%
Exact 95% confidence interval: 0.45%--6.22%
```

After adding structural validation, the same original clean set and the expanded clean set produced no false positives:

```text
Structurally validated rule on original clean set: 0/138 false positives
Structurally validated rule on expanded clean set: 0/600 false positives
Combined structurally validated clean evaluation: 0/738 false positives
Observed combined false-positive rate: 0.00%
Exact 95% confidence interval: 0.00%--0.50%
```

The expanded clean-image evaluation contains 200 additional clean images across four categories:

```text
Camera/natural photographs: 50 images, 150 LSB-depth tests
Screenshots: 50 images, 150 LSB-depth tests
Scanned document-page images: 50 images, 150 LSB-depth tests
Noisy images: 50 images, 150 LSB-depth tests
```

The private camera/natural photograph subset is not publicly released because it may contain identifiable individuals or private visual information. Aggregate results and metadata are provided instead.

### Ablation study

```text
Full system:                 1848/1848, 100.00%
Without deinterleaving:       474/1848, 25.65%
Reduced buffer:               924/1848, 50.00%
Without internal markers:     924/1848, 50.00%
```

### Runtime

```text
Total images processed: 1848
Total runtime: 10169.86 s
Average runtime per image: 5.50 s
Fastest successful detection: 0.17 s
Slowest successful detection: 120.60 s
```

---

## 10. Baseline Tool Comparison

The comparison tools operate under different assumptions:

* `binwalk` scans raw byte streams for contiguous signatures;
* `foremost` performs header/footer-based file carving;
* `exiftool` inspects metadata fields;
* `zsteg` performs LSB-oriented heuristic extraction.

These tools do not perform the same deterministic StegoLSB-compatible bitstream reconstruction, offset handling, and structurally validated file-type attribution used in the proposed method.

In the evaluated dataset:

```text
Proposed method: 1848/1848 (100.00%)
zsteg:            906/1848 (49.03%)
binwalk:            0/1848 (0.00%)
foremost:           0/1848 (0.00%)
exiftool:           0/1848 (0.00%)
```

The result demonstrates that direct raw-byte inspection and metadata analysis are insufficient for file-type attribution when the payload is dispersed across LSB pixel channels. The proposed method reconstructs the hidden byte stream before applying structurally validated file-type attribution.

---

## 11. Robustness and Safe-Failure Behaviour

The robustness/safe-failure analysis evaluated a stratified subset of 36 stego-images under:

* JPEG compression;
* resizing;
* additive noise;
* wrong LSB depth;
* reduced extraction buffer.

Transformations that modify pixel values resulted in failed reconstruction and outputs classified as `UNKNOWN`. These results should be interpreted as **safe failure under tested perturbations**, not broad robustness to transformed stego-images.

The method depends on preserving the original lossless carrier representation.

---

## 12. Known Limitations

The method has the following limitations:

1. It assumes a StegoLSB-compatible sequential embedding model.
2. It requires the correct or tested LSB depth.
3. It depends on lossless image representations.
4. It does not recover encrypted, compressed, or obfuscated payloads if recognisable plaintext file signatures or structures are absent.
5. It is not designed for randomised pixel traversal, adaptive embedding, transform-domain steganography, or lossy JPEG-domain embedding.
6. Variable payload offsets used by other tools may require offset-inference methods such as sliding-window signature search or structural validation across multiple offset hypotheses.
7. The expanded clean-image evaluation improves false-positive assessment, but it remains a finite benchmark and does not represent all possible real-world image acquisition conditions.
8. The private camera/natural photograph subset used for aggregate false-positive testing is withheld from public release for privacy reasons.

---

## 13. Licence

Please refer to the repository licence file for usage terms.
