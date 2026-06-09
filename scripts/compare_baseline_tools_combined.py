import csv
import re
import shutil
import subprocess
from pathlib import Path


# ============================================================
# Project paths
# ============================================================

ROOT = Path("/home/kali/Desktop/stego_dataset_expanded")

MANIFEST = ROOT / "results" / "stego_manifest_combined.csv"
MY_RESULTS = ROOT / "results" / "detection_results_combined.csv"

OUTPUT_PER_FILE = ROOT / "results" / "tool_comparison_per_file.csv"
OUTPUT_SUMMARY = ROOT / "results" / "tool_comparison_summary.csv"

TMP_FOREMOST_ROOT = ROOT / "results" / "tmp_foremost_tool_comparison"

TOOLS = ["proposed_method", "zsteg", "binwalk", "foremost", "exiftool"]


# ============================================================
# Command runner
# ============================================================

def run_cmd(cmd, timeout=180):
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


# ============================================================
# Normalisation helpers
# ============================================================

def normalise_type(value):
    if value is None:
        return "unknown"

    text = str(value).strip().lower()

    if text in {"pdf", "docx", "xlsx", "pptx", "rtf", "exe", "zip", "unknown", "error"}:
        return text

    if "docx" in text or "word" in text:
        return "docx"

    if "xlsx" in text or "excel" in text or "spreadsheet" in text:
        return "xlsx"

    if "pptx" in text or "powerpoint" in text or "presentation" in text:
        return "pptx"

    if "pdf" in text:
        return "pdf"

    if "rtf" in text or "rich text" in text:
        return "rtf"

    if "exe" in text or "pe32" in text or "windows executable" in text or "ms-dos executable" in text:
        return "exe"

    return "unknown"


def remove_filename_artifacts(text, image_path):
    """
    Prevent false positives caused by payload names inside the carrier filename.

    Example problem:
    exiftool prints:
    File Name : Flat-Color_1_S__docx_small__lsb1.bmp

    If the classifier scans that line, it incorrectly predicts DOCX.
    """
    if not text:
        return ""

    path = Path(image_path)

    replacements = {
        str(path),
        path.name,
        path.stem,
    }

    cleaned = text

    for item in replacements:
        if item:
            cleaned = cleaned.replace(item, "")

    return cleaned


def remove_exiftool_filename_lines(text):
    """
    ExifTool reports carrier metadata, not LSB payloads.
    Remove filename/path fields so the classifier does not accidentally detect
    payload labels embedded in filenames.
    """
    lines = []

    for line in text.splitlines():
        lower = line.lower().strip()

        if lower.startswith("file name"):
            continue
        if lower.startswith("directory"):
            continue
        if lower.startswith("source file"):
            continue

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# Tool-specific classifiers
# ============================================================

def classify_zsteg_output(text):
    """
    Classify zsteg output.

    zsteg output contains many candidate streams. We classify only when a
    meaningful payload signature appears in the extracted candidate output.
    """
    lower = text.lower()

    # Office-specific internal markers first
    if "word/" in lower or "word/document.xml" in lower or "docx" in lower:
        return "docx"

    if "xl/" in lower or "xl/workbook.xml" in lower or "xlsx" in lower:
        return "xlsx"

    if "ppt/" in lower or "ppt/presentation.xml" in lower or "pptx" in lower:
        return "pptx"

    # Strong leading signatures exposed in zsteg text/file output
    if "%pdf" in lower or "pdf document" in lower:
        return "pdf"

    if "{\\rtf" in lower or "rich text format" in lower:
        return "rtf"

    # Do not classify every random "mz" substring as EXE.
    # Only accept strong EXE indicators.
    if "pe32 executable" in lower:
        return "exe"

    if "ms-dos executable" in lower:
        return "exe"

    if "windows executable" in lower:
        return "exe"

    # zsteg often prints extracted text in this format:
    # .. text: "MZ..."
    if re.search(r'\.\.\s*text:\s*"mz', lower):
        return "exe"

    # Generic ZIP alone is not enough to distinguish DOCX/XLSX/PPTX
    if "zip archive" in lower or "pk\\x03\\x04" in lower:
        return "zip"

    return "unknown"


def classify_raw_signature_output(text):
    """
    Classify output from raw-byte tools such as binwalk/exiftool.
    This is conservative and avoids counting generic ZIP as Office attribution.
    """
    lower = text.lower()

    # Office-specific markers
    if "word/" in lower or "word/document.xml" in lower:
        return "docx"

    if "xl/" in lower or "xl/workbook.xml" in lower:
        return "xlsx"

    if "ppt/" in lower or "ppt/presentation.xml" in lower:
        return "pptx"

    # Other strong file signatures
    if "%pdf" in lower or "pdf document" in lower:
        return "pdf"

    if "{\\rtf" in lower or "rich text format" in lower:
        return "rtf"

    if "pe32 executable" in lower or "ms-dos executable" in lower or "windows executable" in lower:
        return "exe"

    # Generic ZIP is not enough for DOCX/XLSX/PPTX
    if "zip archive" in lower:
        return "zip"

    return "unknown"


# ============================================================
# Individual tool detectors
# ============================================================

def detect_with_zsteg(image_path):
    """
    Run zsteg in exhaustive mode.

    Manual testing showed that PDF signatures may appear under paths such as:
    b1,r,lsb,xy .. text: "%PDF-1.7..."
    These are visible with zsteg -a, not necessarily with plain zsteg.
    """
    res = run_cmd(["zsteg", "-a", str(image_path)], timeout=240)

    if res is None:
        return "error", "zsteg -a failed or timed out"

    output = (res.stdout + "\n" + res.stderr).strip()
    cleaned = remove_filename_artifacts(output, image_path)

    pred = classify_zsteg_output(cleaned)

    return pred, output


def detect_with_binwalk(image_path):
    res = run_cmd(["binwalk", str(image_path)], timeout=120)

    if res is None:
        return "error", "binwalk failed or timed out"

    output = (res.stdout + "\n" + res.stderr).strip()
    cleaned = remove_filename_artifacts(output, image_path)

    pred = classify_raw_signature_output(cleaned)

    return pred, output


def detect_with_foremost(image_path, index):
    out_dir = TMP_FOREMOST_ROOT / f"foremost_{index:06d}"

    if out_dir.exists():
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    res = run_cmd(
        ["foremost", "-i", str(image_path), "-o", str(out_dir)],
        timeout=180
    )

    if res is None:
        return "error", "foremost failed or timed out"

    found_files = []

    for path in out_dir.rglob("*"):
        if path.is_file():
            found_files.append(path.name.lower())

    joined = " ".join(found_files)

    if any(name.endswith(".pdf") for name in found_files):
        return "pdf", joined

    if any(name.endswith(".rtf") for name in found_files):
        return "rtf", joined

    if any(name.endswith(".exe") for name in found_files):
        return "exe", joined

    if any(name.endswith(".doc") or name.endswith(".docx") for name in found_files):
        return "docx", joined

    if any(name.endswith(".xls") or name.endswith(".xlsx") for name in found_files):
        return "xlsx", joined

    if any(name.endswith(".ppt") or name.endswith(".pptx") for name in found_files):
        return "pptx", joined

    return "unknown", joined


def detect_with_exiftool(image_path):
    """
    ExifTool is a metadata tool. It should not infer payload type from the
    carrier filename. Therefore filename/path fields are removed before
    classification.
    """
    res = run_cmd(["exiftool", str(image_path)], timeout=60)

    if res is None:
        return "error", "exiftool failed or timed out"

    output = (res.stdout + "\n" + res.stderr).strip()

    cleaned = remove_exiftool_filename_lines(output)
    cleaned = remove_filename_artifacts(cleaned, image_path)

    pred = classify_raw_signature_output(cleaned)

    return pred, output


# ============================================================
# Proposed method results
# ============================================================

def load_proposed_predictions():
    predictions = {}

    if not MY_RESULTS.exists():
        print(f"[WARNING] Proposed-method results not found: {MY_RESULTS}")
        return predictions

    with MY_RESULTS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            filename = row.get("stego_filename", "").strip()

            predicted = (
                row.get("predicted_type")
                or row.get("predicted_label")
                or row.get("prediction")
                or ""
            )

            predictions[filename] = normalise_type(predicted)

    return predictions


# ============================================================
# Main
# ============================================================

def main():
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST}")

    OUTPUT_PER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TMP_FOREMOST_ROOT.mkdir(parents=True, exist_ok=True)

    proposed_predictions = load_proposed_predictions()

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))

    total_samples = len(manifest_rows)

    print(f"Loaded manifest rows: {total_samples}")
    print(f"Manifest: {MANIFEST}")
    print()

    summary = {
        tool: {
            "correct": 0,
            "total": 0,
            "unknown": 0,
            "error": 0,
            "zip_only": 0
        }
        for tool in TOOLS
    }

    per_file_rows = []

    for index, row in enumerate(manifest_rows, start=1):
        stego_filename = row["stego_filename"]
        stego_path = Path(row["stego_path"])
        expected = normalise_type(row["expected_type"])

        print(f"[{index}/{total_samples}] {stego_filename}")

        tool_outputs = {}

        # Proposed method
        proposed_pred = proposed_predictions.get(stego_filename, "unknown")
        tool_outputs["proposed_method"] = (
            proposed_pred,
            "Loaded from detection_results_combined.csv"
        )

        # External tools
        tool_outputs["zsteg"] = detect_with_zsteg(stego_path)
        tool_outputs["binwalk"] = detect_with_binwalk(stego_path)
        tool_outputs["foremost"] = detect_with_foremost(stego_path, index)
        tool_outputs["exiftool"] = detect_with_exiftool(stego_path)

        for tool, (predicted, raw_output) in tool_outputs.items():
            predicted = normalise_type(predicted)

            correct = int(predicted == expected)

            summary[tool]["total"] += 1
            summary[tool]["correct"] += correct

            if predicted == "unknown":
                summary[tool]["unknown"] += 1

            if predicted == "error":
                summary[tool]["error"] += 1

            if predicted == "zip":
                summary[tool]["zip_only"] += 1

            per_file_rows.append({
                "stego_filename": stego_filename,
                "stego_path": str(stego_path),
                "cover_filename": row.get("cover_filename", ""),
                "cover_category": row.get("cover_category", ""),
                "cover_format": row.get("cover_format", ""),
                "payload_filename": row.get("payload_filename", ""),
                "payload_type": row.get("payload_type", ""),
                "payload_size_class": row.get("payload_size_class", ""),
                "lsb": row.get("lsb", ""),
                "expected_type": expected,
                "tool": tool,
                "predicted_type": predicted,
                "correct": correct,
                "raw_output": str(raw_output).replace("\n", " ")[:3000]
            })

    # ========================================================
    # Write detailed per-file output
    # ========================================================

    fieldnames = [
        "stego_filename",
        "stego_path",
        "cover_filename",
        "cover_category",
        "cover_format",
        "payload_filename",
        "payload_type",
        "payload_size_class",
        "lsb",
        "expected_type",
        "tool",
        "predicted_type",
        "correct",
        "raw_output"
    ]

    with OUTPUT_PER_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_file_rows)

    # ========================================================
    # Write summary output
    # ========================================================

    with OUTPUT_SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "tool",
            "correct",
            "total",
            "accuracy_percent",
            "unknown",
            "errors",
            "zip_only"
        ])

        for tool in TOOLS:
            correct = summary[tool]["correct"]
            total = summary[tool]["total"]
            accuracy = (correct / total) * 100 if total else 0

            writer.writerow([
                tool,
                correct,
                total,
                f"{accuracy:.2f}",
                summary[tool]["unknown"],
                summary[tool]["error"],
                summary[tool]["zip_only"]
            ])

    # ========================================================
    # Terminal summary
    # ========================================================

    print()
    print("==================== TOOL COMPARISON SUMMARY ====================")

    for tool in TOOLS:
        correct = summary[tool]["correct"]
        total = summary[tool]["total"]
        accuracy = (correct / total) * 100 if total else 0

        print(f"{tool:16s}: {correct}/{total} ({accuracy:.2f}%)")

    print()
    print(f"Detailed results saved : {OUTPUT_PER_FILE}")
    print(f"Summary saved          : {OUTPUT_SUMMARY}")
    print("==================================================================")


if __name__ == "__main__":
    main()
