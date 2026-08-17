# LSB Stego Detector: Bitstream Reconstruction for File-Type Attribution

This repository contains the source code, experimental scripts, payload files, manifests, result outputs, and reproducibility documentation for the project:

**Decoding Hidden Structures: Bitstream Reconstruction for File-Type Attribution in LSB Steganography**

The project implements a deterministic reconstruction-based forensic pipeline for identifying concealed file types embedded in images using Least Significant Bit (LSB) steganography.

Unlike conventional forensic tools that inspect the carrier image as a contiguous byte stream or metadata object, the proposed method first reconstructs the StegoLSB-compatible hidden bitstream and then performs file-type attribution on the reconstructed payload.

The revised authoritative implementation reconstructs and decodes the StegoLSB payload-length tag, validates the declared payload size against carrier capacity, reconstructs the declared payload, and applies format-specific structural validation.

The supported payload classes in the reported experiment are:

- PDF
- DOCX
- XLSX
- PPTX
- RTF
- EXE

The repository also contains auxiliary ablation, safe-failure, runtime, dataset-generation, and comparison experiments.

---

## 1. Authoritative Revised Implementation

The quantitative **primary stego-image and clean-image results reported in the revised manuscript** are generated using one shared authoritative implementation:

```text
scripts/authoritative_detector.py
scripts/run_authoritative_stego.py
scripts/run_authoritative_clean.py
```

The corresponding authoritative result files are:

```text
results/authoritative_stego_1848.csv
results/authoritative_stego_summary.csv
results/authoritative_clean_738.csv
results/authoritative_clean_summary.csv
results/authoritative_clean_manifest_246.csv
results/authoritative_code_hashes.txt
```

The exact 1,848-sample stego-image evaluation set is defined by:

```text
results/stego_manifest_combined.csv
```

### Important distinction

The scripts listed above are the authoritative source for the **primary revised quantitative results**.

Several older detector and batch scripts remain in the repository for development provenance, GUI demonstration, earlier experiments, ablation variants, or auxiliary analysis. They should not be used to reproduce the revised 1,848-image main result or the revised 738-test clean-image result.

---

## 2. Authoritative Reconstruction Procedure

For an image analysed at LSB depth `l`, the authoritative detector performs the following operations:

1. Opens the suspected PNG/BMP image.
2. Flattens pixels using the StegoLSB-compatible raster/channel traversal order.
3. Extracts and deinterleaves the selected LSB depth.
4. Computes the StegoLSB payload-length-tag width.
5. Reconstructs the payload-length tag.
6. Decodes the tag using the fixed **little-endian** byte order of the experimental generation environment.
7. Validates the declared payload length against the available carrier capacity.
8. Reconstructs up to the first 16 payload bytes as a supported-signature pre-check.
9. If the supported signature pre-check succeeds, reconstructs exactly the declared payload.
10. Applies format-specific structural validation.
11. Returns a validated file type or `Unknown/None`.

The authoritative implementation **does not use the earlier fixed 10,000-byte inspection window** for the principal revised experiments.

### Structural validation rules

The following validation logic is applied:

- **PDF**
  - `%PDF` leading signature
  - `startxref`
  - terminal `%%EOF`

- **DOCX / XLSX / PPTX**
  - valid ZIP container
  - `[Content_Types].xml`
  - subtype-specific structure:
    - `word/` → DOCX
    - `xl/` → XLSX
    - `ppt/` → PPTX

- **EXE**
  - `MZ` DOS header
  - `e_lfanew` offset
  - `PE\x00\x00` signature at the referenced offset

- **RTF**
  - `{\rtf1` leading signature
  - plausible RTF control or terminal structure

If the declared length is invalid, no supported leading signature is found, or the structural validator rejects the reconstructed payload, the detector returns:

```text
Unknown/None
```

rather than assigning an unsupported file-type label.

---

## 3. Scope of the Method

The proposed detector is evaluated under **controlled StegoLSB-compatible sequential embedding conditions**.

The reported method assumes:

- lossless PNG or BMP image carriers;
- deterministic sequential StegoLSB-compatible traversal;
- a known or examiner-tested LSB depth;
- embedding depths of 1, 2, or 3 LSBs per channel;
- the StegoLSB v1.7.1 payload-size-tag convention;
- unencrypted payloads;
- no pre-embedding payload obfuscation;
- no destructive image transformation before analysis.

The method should therefore be interpreted as a:

**forensic file-type attribution framework under a compatible embedding model**

and not as a universal detector for all forms of image steganography.

The present implementation does not claim general support for:

- pseudo-random traversal;
- key-dependent traversal;
- unrelated steganographic embedding tools;
- encrypted payloads;
- arbitrary compressed outer payloads where the original inner file type is required;
- unknown or variable payload offsets;
- adaptive embedding;
- transform-domain steganography;
- lossy JPEG-domain embedding;
- resizing;
- recompression;
- post-embedding pixel modification.

These cases require additional traversal inference, offset inference, decryption/decompression, or tool-specific extraction logic.

---

## 4. Repository Structure

```text
lsb-stego-detector/
│
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
│   ├── authoritative_stego_1848.csv
│   ├── authoritative_stego_summary.csv
│   ├── authoritative_clean_738.csv
│   ├── authoritative_clean_summary.csv
│   ├── authoritative_clean_manifest_246.csv
│   ├── authoritative_code_hashes.txt
│   ├── stego_manifest_combined.csv
│   │
│   ├── ablation_results_per_file.csv
│   ├── ablation_results_summary.csv
│   ├── confusion_matrix.csv
│   ├── cover_dimensions_and_modes.csv
│   ├── detection_results_combined.csv
│   ├── embedding_plan_combined.csv
│   ├── false_positive_analysis.csv
│   ├── false_positive_clean_results.csv
│   ├── payload_sizes_and_hashes.csv
│   ├── robustness_results_per_file.csv
│   ├── robustness_selected_subset.csv
│   ├── robustness_table.csv
│   ├── runtime_per_file.csv
│   ├── runtime_summary.csv
│   ├── structural_validation_stego_1848.csv
│   └── structural_validation_summary.csv
│
├── scripts/
│   ├── authoritative_detector.py
│   ├── run_authoritative_stego.py
│   ├── run_authoritative_clean.py
│   │
│   ├── build_combined_embedding_plan.py
│   ├── build_stego_manifest_combined.py
│   ├── compare_baseline_tools_combined.py
│   ├── detector_ablation.py
│   ├── run_ablation_study.py
│   ├── run_robustness_analysis.py
│   │
│   ├── detector_cli.py
│   ├── run_detection_combined.py
│   ├── run_false_positive_clean.py
│   ├── run_runtime_analysis.py
│   ├── run_structural_validation_1848.py
│   ├── main.py
│   └── updated_main.py
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

## 5. Primary vs Legacy / Auxiliary Scripts

The following files are authoritative for the principal revised experiments:

```text
scripts/authoritative_detector.py
scripts/run_authoritative_stego.py
scripts/run_authoritative_clean.py
```

The following scripts should **not** be used to reproduce the revised 1,848-image primary attribution result or the revised 738-test clean-image result:

```text
scripts/detector_cli.py
scripts/run_detection_combined.py
scripts/run_false_positive_clean.py
scripts/run_structural_validation_1848.py
scripts/run_runtime_analysis.py
scripts/main.py
```

These scripts represent earlier stages of development or auxiliary functionality and are retained for provenance and project history.

The following scripts are used for separate internal experimental analyses:

```text
scripts/detector_ablation.py
scripts/run_ablation_study.py
scripts/run_robustness_analysis.py
```

These should be interpreted as **internal ablation or perturbation analyses**, not as independent external comparison tools.

---

## 6. Dataset and Payload Composition

The controlled carrier set contains:

```text
46 images
```

consisting of:

```text
16 original controlled carriers
30 high-resolution XL synthetic carriers
```

The evaluation includes six payload types:

```text
PDF
DOCX
XLSX
PPTX
RTF
EXE
```

Each file type is represented by:

```text
small
medium
large
```

payload sizes.

Three LSB embedding depths are evaluated:

```text
1 LSB
2 LSBs
3 LSBs
```

Under ideal execution:

```text
46 covers
× 6 payload types
× 3 payload sizes
× 3 LSB depths
= 2,484 planned embedding cases
```

The final valid dataset contains:

```text
1,848 valid stego-images
```

The reduction from 2,484 planned cases to 1,848 valid stego-images is due to:

1. carrier-capacity limitations, where the payload exceeded the available embedding capacity; and
2. a StegoLSB v1.7.1 limitation affecting certain scalar greyscale PNG embedding attempts.

Only successfully generated stego-images are included in the final manifest-defined evaluation.

---

## 7. Carrier Image Composition

The 46 controlled carriers consist of:

```text
23 BMP images
23 PNG images
45 RGB images
1 greyscale L-mode image
```

Carrier dimensions range approximately from:

```text
512 × 512 pixels
```

to:

```text
5926 × 5926 pixels
```

The original controlled set contains the following visual categories:

```text
Flat-Colour
Greyscale
High-Detail
Low-Detail
Mixed-Content
Noisy
Photographic
Transparency
```

The 30-image XL synthetic extension was created to provide sufficient capacity for medium and large payload experiments.

---

## 8. Exact Payload Sizes

| Payload | Small (bytes) | Medium (bytes) | Large (bytes) |
|---|---:|---:|---:|
| DOCX | 13,432 | 511,127 | 1,121,154 |
| PDF | 16,620 | 510,410 | 1,100,144 |
| XLSX | 8,899 | 511,280 | 1,090,468 |
| PPTX | 32,020 | 512,113 | 1,082,610 |
| RTF | 50,275 | 511,504 | 1,085,026 |
| EXE | 40,448 | 505,856 | 1,017,856 |

The payload-size classes therefore occupy the following ranges:

```text
Small:
8,899–50,275 bytes

Medium:
505,856–512,113 bytes

Large:
1,017,856–1,121,154 bytes
```

Additional payload hashes and carrier metadata are provided in:

```text
results/payload_sizes_and_hashes.csv
results/cover_dimensions_and_modes.csv
```

---

## 9. Clean-Image Evaluation

The authoritative clean-image evaluation contains:

```text
246 unique clean images
```

### Original controlled clean set

```text
46 clean images
× 3 tested LSB depths
= 138 clean-image tests
```

These correspond to the controlled carrier images before embedding.

### Expanded independent clean set

```text
200 clean images
× 3 tested LSB depths
= 600 clean-image tests
```

The expanded independent clean set contains:

```text
Camera/natural photographs: 50
Screenshots:                 50
Scanned document pages:      50
Noisy images:                50
```

### Combined clean evaluation

```text
246 unique clean images
738 clean-image test cases
```

The authoritative structurally validated detector produced:

```text
Original controlled set:
0/138 false positives

Expanded independent set:
0/600 false positives

Combined:
0/738 false positives

Observed false-positive rate:
0.00%

Exact two-sided 95% CI:
approximately 0.00%–0.50%

Processing errors:
0
```

This should be interpreted as **zero observed false positives within the evaluated clean-image corpus**, not as evidence that the true false-positive probability is zero for unrestricted forensic data.

An earlier development implementation produced a different result on the original clean-image experiment. That value is retained only as historical development provenance and is **not the authoritative false-positive estimate for the revised method**.

---

## 10. Data Availability

This GitHub repository contains:

- source code;
- authoritative detector and experiment runners;
- sample cover images;
- sample stego-images;
- benign payload examples;
- manifests;
- quantitative result CSV files;
- metadata;
- implementation hashes;
- tool-version documentation;
- reproduction documentation.

The complete generated stego-image archive is not stored directly in GitHub because of repository-size considerations.

The public dataset is available separately through Kaggle:

```text
https://www.kaggle.com/datasets/arkapaul2514/lsb-stego-attribution-and-evaluation-dataset
```

The public dataset contains the 1,848 valid stego-images used in the main attribution evaluation together with public clean-image material.

The 50 camera/natural photograph images used in the expanded clean-image evaluation are not publicly distributed because some may contain identifiable individuals or private visual information.

These images were used only for aggregate false-positive analysis and were not used for:

```text
stego-image generation
model training
detector training
method tuning
payload attribution development
```

No personal data from the withheld subset are included in the public repository.

---

## 11. Payload Files

The directory:

```text
dataset/sample_payloads/
```

contains benign synthetic payload files used for controlled experiments.

Payloads are organised by:

```text
file type
size class
```

The EXE payloads are harmless test executables used only for PE-format attribution experiments. They are not malware.

Recorded SHA-256 hashes include:

```text
medium/P06.exe
8dbba6af13993a1c9eb868ded6a68101c036f025aefe055ac98932ebe6233366

large/P06.exe
68dce1774763ef5c2ed853d26b6d0a9d1f9e70cb83f08b7e5c28069aa0b92bb3

small/P06.exe
e99c275bc74742ccaf781942ee66a06e6da063ceacb9165d61ee67fc84b3558d
```

---

## 12. Authoritative Detector Files

### Shared authoritative detector

```text
scripts/authoritative_detector.py
```

This file implements the shared reconstruction and structural-attribution logic.

### Authoritative stego-image runner

```text
scripts/run_authoritative_stego.py
```

The runner:

- reads `results/stego_manifest_combined.csv`;
- requires exactly 1,848 manifest rows;
- resolves each manifest-defined stego-image;
- evaluates each sample once at its recorded embedding depth;
- invokes the shared authoritative detector;
- records payload length;
- records tag endianness;
- records structural-validation status;
- records runtime;
- records attribution correctness.

Outputs:

```text
results/authoritative_stego_1848.csv
results/authoritative_stego_summary.csv
```

### Authoritative clean-image runner

```text
scripts/run_authoritative_clean.py
```

The runner evaluates:

```text
46 original clean images
+
200 expanded independent clean images
=
246 clean images
```

at:

```text
1 LSB
2 LSBs
3 LSBs
```

producing:

```text
738 clean-image tests
```

Outputs:

```text
results/authoritative_clean_738.csv
results/authoritative_clean_summary.csv
results/authoritative_clean_manifest_246.csv
```

---

## 13. GUI Implementations

The repository also contains GUI-oriented detector implementations:

```text
scripts/main.py
scripts/updated_main.py
```

These are retained for interactive demonstration and development history.

They are not the source of the revised primary quantitative results.

For reproducibility of the revised manuscript results, use:

```text
scripts/authoritative_detector.py
scripts/run_authoritative_stego.py
scripts/run_authoritative_clean.py
```

---

## 14. Reproducibility Environment

The authoritative experiment was executed using:

```text
Operating system:
Kali GNU/Linux Rolling 2025.4

Kernel:
Linux 6.18.3+kali+1-amd64

Python:
3.13.11

Pillow:
12.0.0

NumPy:
2.3.5

Pandas:
2.3.3

stego-lsb:
1.7.1
```

StegoLSB functionality was obtained from:

```text
ragibson/Steganography
```

Relevant functions include:

```text
lsb_interleave_list
lsb_deinterleave_list
roundup
```

The experiment-generation environment is little-endian.

The authoritative detector therefore explicitly fixes the StegoLSB payload-length-tag interpretation to:

```text
little-endian
```

This ensures that rerunning the detector on another architecture does not silently change the experimental size-tag interpretation.

---

## 15. Installation

Install Python dependencies with:

```bash
pip install -r requirements.txt
```

The external forensic tools used for comparison are:

```text
zsteg
binwalk
foremost
exiftool
```

Typical installation on Kali Linux:

```bash
sudo apt update
sudo apt install binwalk foremost exiftool
gem install zsteg
```

Tool and environment information is documented in:

```text
docs/tool_versions.md
```

---

## 16. Dataset Path Configuration

The authoritative experiment was originally executed with the complete dataset located at:

```text
/home/kali/stego_dataset_expanded
```

The current runner scripts define the dataset root near the top of each script.

When reproducing the experiment on another system, change the dataset root to the local dataset location.

The local filesystem location is **not part of the detection algorithm**.

The authoritative 1,848-image experiment is defined using:

```text
results/stego_manifest_combined.csv
```

rather than recursively treating every file found in a dataset directory as an experimental sample.

This guarantees that the reported experiment consists of the exact manifest-defined 1,848 valid stego-images.

---

## 17. Reproducing the Primary Revised Results

### Step 1: Verify required files

Ensure that these files exist:

```text
scripts/authoritative_detector.py
scripts/run_authoritative_stego.py
scripts/run_authoritative_clean.py
results/stego_manifest_combined.csv
```

The complete image dataset must also be available locally.

### Step 2: Run authoritative stego-image evaluation

```bash
python3 scripts/run_authoritative_stego.py
```

Expected outputs:

```text
results/authoritative_stego_1848.csv
results/authoritative_stego_summary.csv
```

Expected principal result:

```text
Samples tested:         1,848
Correct attributions:   1,848
Incorrect attributions: 0
Processing errors:      0
Accuracy:               100.00%
```

### Step 3: Run authoritative clean-image evaluation

```bash
python3 scripts/run_authoritative_clean.py
```

Expected outputs:

```text
results/authoritative_clean_738.csv
results/authoritative_clean_summary.csv
results/authoritative_clean_manifest_246.csv
```

Expected principal result:

```text
Unique clean images: 246
Clean-image tests:   738
False positives:     0
Observed FPR:        0.00%
Processing errors:   0
```

### Step 4: Verify implementation hashes

Authoritative implementation hashes are recorded in:

```text
results/authoritative_code_hashes.txt
```

Current SHA-256 values:

```text
f52d19aeebf69a93edbe66b1511fb68c99fd0178cc4e08881a395a207f16ef41  scripts/authoritative_detector.py

37617e3101f97e4807d789cd8759e73ea2829a82d40a61ec89a08ad592f0e327  scripts/run_authoritative_stego.py

d0aa6dd4a59ef3dda1c2e134b5b3549f3a0e45bb1e2485c2bcf0bb6175a960c0  scripts/run_authoritative_clean.py
```

If these scripts are deliberately modified after this revision, regenerate the hash file and record the corresponding Git commit.

---

## 18. Authoritative Main Experimental Results

### Overall attribution

```text
Manifest rows:          1,848
Samples tested:         1,848
Correct attributions:   1,848
Incorrect attributions: 0
Processing errors:      0
Observed accuracy:      100.00%
```

The exact two-sided binomial 95% confidence interval is approximately:

```text
99.80%–100.00%
```

This should be interpreted as complete observed attribution under the evaluated StegoLSB-compatible sequential embedding conditions.

It should not be interpreted as evidence of zero expected error for unrestricted real-world steganography.

### Payload-level performance

```text
PDF:  308/308
DOCX: 308/308
XLSX: 308/308
PPTX: 308/308
RTF:  308/308
EXE:  308/308
```

### LSB-depth performance

```text
1-LSB:
474/474

2-LSB:
624/624

3-LSB:
750/750
```

### Carrier-format performance

```text
BMP:
1,068/1,068

PNG:
780/780
```

### Payload-length-tag byte order

```text
little-endian:
1,848/1,848
```

---

## 19. Authoritative Runtime Results

The revised runtime measurements were generated during the authoritative 1,848-image evaluation.

```text
Total images processed:
1,848

Total runtime:
7,553.390136 seconds

Mean runtime per image:
4.087151 seconds

Median runtime per image:
1.229321 seconds

Minimum runtime:
0.124609 seconds

Maximum runtime:
30.456203 seconds
```

Rounded manuscript values:

```text
Total runtime:
7,553.39 s

Mean:
4.087 s/image

Median:
1.229 s/image

Minimum:
0.125 s

Maximum:
30.456 s
```

The authoritative revised runtime values are stored in:

```text
results/authoritative_stego_1848.csv
results/authoritative_stego_summary.csv
```

Earlier files such as:

```text
results/runtime_per_file.csv
results/runtime_summary.csv
```

are retained only as historical experimental outputs and are not the authoritative runtime values for the revised main experiment.

---

## 20. External Tool Comparison

The external tool comparison is intended as a **capability and representation comparison**, not as a claim that every evaluated tool solves the same forensic task.

The evaluated public tools are:

```text
zsteg
binwalk
foremost
exiftool
```

### zsteg

`zsteg` is retained as the closest publicly available LSB-oriented comparison utility used in the study.

The reported configuration is:

```bash
zsteg -a <image_path>
```

Its output was examined for recognised payload signatures and subtype evidence.

### binwalk

`binwalk` operates primarily on byte-aligned data and known embedded structures.

### foremost

`foremost` performs header/footer-oriented carving of contiguous byte streams.

### exiftool

`exiftool` inspects file-format structures and metadata.

These tools do not implement the same complete pipeline used by the proposed method:

```text
StegoLSB-compatible raster/channel traversal
→
LSB deinterleaving
→
payload-size-tag decoding
→
declared-length reconstruction
→
file signature analysis
→
format-specific structural validation
```

### Observed comparison results

```text
Proposed method:
1,848/1,848
100.00%

zsteg:
906/1,848
49.03%

binwalk:
0/1,848
0.00%

foremost:
0/1,848
0.00%

exiftool:
0/1,848
0.00%
```

No internally modified version of the proposed detector is presented as though it were an independent external comparison tool.

Internal component removals and restrictions are evaluated separately through the ablation study.

---

## 21. Ablation Study

The repository retains the internal component-analysis experiment reported in the manuscript.

Reported results:

```text
Full system:
1,848/1,848
100.00%

Without deinterleaving:
474/1,848
25.65%

Reduced buffer / partial extraction:
924/1,848
50.00%

Without internal markers:
924/1,848
50.00%
```

These configurations are internal experimental ablations.

They are **not independent external baseline tools**.

Relevant files include:

```text
scripts/detector_ablation.py
scripts/run_ablation_study.py

results/ablation_results_per_file.csv
results/ablation_results_summary.csv
```

The authoritative primary stego-image and clean-image results must instead be reproduced using:

```text
scripts/authoritative_detector.py
scripts/run_authoritative_stego.py
scripts/run_authoritative_clean.py
```

---

## 22. Safe-Failure / Perturbation Analysis

A stratified subset of:

```text
36 stego-images
```

was used to examine behaviour when assumptions needed for successful reconstruction are deliberately violated.

The evaluated scenarios include:

```text
Original
Reduced Buffer / Partial Extraction
JPEG Compression
Resizing
Slight Noise
Wrong LSB Depth
```

Reported results:

```text
Original:
36/36 correct

Reduced Buffer / Partial Extraction:
18/36 correct
18 Unknown

JPEG Compression:
0/36 correct
36 Unknown

Resizing:
0/36 correct
36 Unknown

Slight Noise:
0/36 correct
36 Unknown

Wrong LSB Depth:
0/36 correct
36 Unknown
```

The transformed and wrong-depth cases did not produce unsupported target file-type labels in the evaluated subset.

They resulted in:

```text
Unknown
```

instead.

These results should be interpreted as **safe-failure behaviour under selected perturbations**, not as evidence of broad robustness.

Relevant files include:

```text
scripts/run_robustness_analysis.py

results/robustness_results_per_file.csv
results/robustness_selected_subset.csv
results/robustness_table.csv
```

---

## 23. Legacy / Development Outputs

Several earlier output files remain in the repository to preserve project provenance.

These include:

```text
results/detection_results_combined.csv
results/false_positive_clean_results.csv
results/false_positive_analysis.csv
results/structural_validation_stego_1848.csv
results/structural_validation_summary.csv
results/runtime_per_file.csv
results/runtime_summary.csv
```

These files should not be confused with the authoritative primary revised outputs.

For the revised principal results, use:

```text
results/authoritative_stego_1848.csv
results/authoritative_stego_summary.csv

results/authoritative_clean_738.csv
results/authoritative_clean_summary.csv
results/authoritative_clean_manifest_246.csv

results/authoritative_code_hashes.txt
```

---

## 24. Known Limitations

The current framework has the following limitations:

1. It assumes a StegoLSB-compatible sequential embedding model.
2. It requires the correct or explicitly tested LSB depth.
3. It depends on lossless preservation of the carrier image.
4. It does not identify the original plaintext file type when encryption removes recognisable plaintext signatures unless an appropriate decryption stage is available.
5. When a payload is compressed before embedding, the reconstructed object may expose the compressed or container format rather than the original inner file type.
6. Pseudo-random or key-dependent traversal requires recovery or inference of the traversal order.
7. The method is not currently designed for adaptive or transform-domain embedding.
8. The method is not robust to JPEG recompression, resizing, or pixel-level modification.
9. Variable payload offsets and unrelated embedding-tool metadata layouts require additional inference.
10. The clean-image corpus remains finite and cannot represent all possible real-world acquisition conditions.
11. The private camera/natural-photograph subset is withheld from public release for privacy reasons.

---

## 25. Future Work

Future research should investigate:

```text
automatic LSB-depth inference
variable-offset inference
sliding-window signature analysis
pseudo-random traversal recovery
key-hypothesis testing
support for additional embedding tools
decompression/container inspection
encrypted-payload workflows where keys are available
additional payload classes
larger independent clean-image corpora
additional forensic acquisition conditions
more diverse carrier devices and formats
```

These extensions are required before the framework can be generalised beyond the controlled StegoLSB-compatible sequential embedding model evaluated in the current study.

---

## 26. Reproducibility Notes

For the principal revised experiment:

- use the exact manifest-defined 1,848-sample evaluation set;
- use the embedding depth recorded in the manifest;
- use `scripts/authoritative_detector.py`;
- use explicit little-endian size-tag decoding;
- preserve StegoLSB-compatible raster/channel traversal;
- preserve the six target payload classes;
- keep processing errors separate from false-positive attributions;
- do not include unrelated files discovered elsewhere in the dataset directory;
- record the Git commit corresponding to the experiment.

The principal attribution experiment is deterministic and does not require random sampling.

Where Gaussian noise is used in the auxiliary perturbation experiment, the pseudo-random generator seed is fixed to:

```text
42
```

---

## 27. Licence

Please refer to the repository licence file for usage terms.

---

## 28. Citation

If you use this repository or dataset in academic work, please cite the associated manuscript:

**Decoding Hidden Structures: Bitstream Reconstruction for File-Type Attribution in LSB Steganography**

A final publication citation and DOI can be added here once available.
