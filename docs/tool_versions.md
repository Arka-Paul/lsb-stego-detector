# Tool Versions and Experimental Environment

This document records the software environment, external forensic tools, embedding library, and hardware configuration used for the experiments in the LSB stego detector project.

---

## 1. Repository Version

The environment information was recorded from the following repository commit:

```text
1c497f3d4b5bbb04036156b64498ab785c95f608
```

Later documentation-only commits may have a different Git commit hash.

---

## 2. Operating System

```text
Operating system: Kali GNU/Linux Rolling
Version: 2025.4
Kernel: Linux kali 6.18.3+kali+1-amd64
Architecture: x86_64
```

Recorded command output:

```text
Linux kali 6.18.3+kali+1-amd64 #1 SMP PREEMPT_DYNAMIC Kali 6.18.3-1kali2 (2026-01-14) x86_64 GNU/Linux
PRETTY_NAME="Kali GNU/Linux Rolling"
VERSION_ID="2025.4"
VERSION="2025.4"
VERSION_CODENAME=kali-rolling
```

---

## 3. Python Environment

```text
Python: 3.13.11
pip: 25.3
```

Recorded command output:

```text
Python 3.13.11
pip 25.3 from /usr/lib/python3/dist-packages/pip (python 3.13)
```

---

## 4. Python Packages

The following Python packages were used during implementation and evaluation:

```text
Pillow: 12.0.0
NumPy: 2.3.5
Pandas: 2.3.3
stego-lsb: 1.7.1
```

Package locations:

```text
Pillow location: /usr/lib/python3/dist-packages
NumPy location: /usr/lib/python3/dist-packages
Pandas location: /usr/lib/python3/dist-packages
stego-lsb location: /home/kali/.local/lib/python3.13/site-packages
```

---

## 5. StegoLSB / stego-lsb Embedding Tool

The embedding and LSB deinterleaving functionality used in this project was based on the `stego-lsb` package from the following source repository:

```text
Source repository: https://github.com/ragibson/Steganography
Python package: stego-lsb
Installed version: 1.7.1
Command-line tool: stegolsb
```

Recorded command output:

```text
stegolsb, version 1.7.1
```

Imported package path:

```text
/home/kali/.local/lib/python3.13/site-packages/stego_lsb/__init__.py
```

Relevant functions used in this project:

```text
lsb_interleave_list
lsb_deinterleave_list
roundup
```

These functions were used for StegoLSB-compatible payload embedding, bitstream extraction, deinterleaving, and reconstruction.

---

## 6. zsteg

```text
Executable path: /usr/local/bin/zsteg
Ruby version: ruby 3.3.8
zsteg gem version: 0.2.14
```

Recorded command output:

```text
zsteg: version unknown
ruby 3.3.8 (2025-04-09 revision b200bad6cd) [x86_64-linux-gnu]
zsteg (0.2.14)
```

Configuration used for baseline comparison:

```bash
zsteg -a <image_path>
```

The `-a` option was used to perform exhaustive analysis across candidate bit-plane, channel, and extraction configurations.

---

## 7. Binwalk

```text
Executable path: /usr/bin/binwalk
Package version: 2.4.3+dfsg1-2
```

Recorded command output:

```text
binwalk 2.4.3+dfsg1-2
```

Configuration used for baseline comparison:

```bash
binwalk <image_path>
```

Binwalk was evaluated as a traditional raw-byte signature scanning baseline. It does not reconstruct LSB bitstreams before analysis.

---

## 8. Foremost

```text
Executable path: /usr/bin/foremost
Version: 1.5.7
```

Recorded command output:

```text
1.5.7
```

Configuration used for baseline comparison:

```bash
foremost -i <image_path> -o <output_directory>
```

Foremost was evaluated as a header-footer file carving baseline. It assumes recoverable files exist as contiguous byte sequences.

---

## 9. ExifTool

```text
Executable path: /usr/bin/exiftool
Version: 13.44
```

Recorded command output:

```text
13.44
```

Configuration used for baseline comparison:

```bash
exiftool <image_path>
```

ExifTool was evaluated as a metadata inspection baseline. It does not analyse pixel-level LSB payloads.

---

## 10. Hardware Configuration

Runtime measurements were collected on the following hardware:

```text
CPU: AMD Ryzen 5 3500U with Radeon Vega Mobile Gfx
Architecture: x86_64
Logical CPUs: 4
Threads per core: 1
Cores per socket: 2
Sockets: 2
RAM: 7.7 GiB
Swap: 953 MiB
```

Recorded memory output:

```text
Mem: 7.7Gi total, 1.4Gi used, 5.0Gi free, 6.4Gi available
Swap: 953Mi total, 0B used, 953Mi free
```

Storage status at the time of recording:

```text
Filesystem: /dev/sda1
Size: 79G
Used: 74G
Available: 1.2G
Use: 99%
```

The low available disk space should be considered when regenerating the full dataset or running scripts that create temporary output files, such as `foremost` comparison runs.

---

## 11. Runtime Summary

The runtime experiment reported the following results:

```text
Total images processed: 1848
Correct detections: 1848
Incorrect detections: 0
Total runtime: 10169.86 seconds
Average runtime per image: 5.50 seconds
Fastest successful runtime: 0.17 seconds
Slowest successful runtime: 120.60 seconds
```

Runtime results depend on hardware, storage speed, Python environment, image dimensions, and extraction workload.

---

## 12. Reproducibility Notes

All reported results should be interpreted under controlled StegoLSB-compatible sequential embedding conditions.

The comparison tools were included to evaluate behaviour under different forensic assumptions:

```text
zsteg: LSB-aware heuristic extraction
binwalk: raw-byte signature scanning
foremost: header-footer file carving
exiftool: metadata inspection
proposed method: StegoLSB-compatible LSB bitstream reconstruction followed by file-type attribution
```

The proposed method reconstructs candidate payload bytes before applying signature-based attribution, whereas the traditional forensic tools operate directly on the carrier file or metadata.
