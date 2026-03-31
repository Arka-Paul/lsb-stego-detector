import csv
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

STEGO_DIR = REPO_ROOT / "dataset" / "sample_stego"
GROUND_TRUTH = REPO_ROOT / "dataset" / "ground_truth.csv"
MY_RESULTS = REPO_ROOT / "results" / "example_outputs" / "detection_results.csv"

OUTPUT_PER_FILE = REPO_ROOT / "results" / "example_outputs" / "tool_comparison_per_file.csv"
OUTPUT_SUMMARY = REPO_ROOT / "results" / "example_outputs" / "tool_comparison_summary.csv"

TMP_DIR = REPO_ROOT / "results" / "tmp_foremost"

TOOLS = ["my_tool", "zsteg", "binwalk", "foremost", "exiftool"]


def run_cmd(cmd, timeout=60):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return result
    except Exception:
        return None


def detect_with_zsteg(image_path):
    res = run_cmd(["zsteg", str(image_path)])

    if res is None:
        return "error"

    text = (res.stdout + res.stderr).lower()

    if "pdf" in text:
        return "pdf"
    if "rtf" in text:
        return "rtf"
    if "exe" in text or "mz" in text:
        return "exe"
    if "word/" in text or "docx" in text:
        return "docx"
    if "xl/" in text or "xlsx" in text:
        return "xlsx"
    if "ppt/" in text or "pptx" in text:
        return "pptx"

    return "unknown"


def detect_with_binwalk(image_path):
    res = run_cmd(["binwalk", str(image_path)])

    if res is None:
        return "error"

    text = (res.stdout + res.stderr).lower()

    if "pdf" in text:
        return "pdf"
    if "rtf" in text:
        return "rtf"
    if "pe32" in text or "exe" in text:
        return "exe"

    # Binwalk often detects ZIP containers but may not distinguish
    # DOCX/XLSX/PPTX reliably without deeper container inspection.
    if "zip archive" in text:
        return "docx"

    return "unknown"


def detect_with_foremost(image_path):
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    res = run_cmd(["foremost", "-i", str(image_path), "-o", str(TMP_DIR)])

    if res is None:
        return "error"

    for file_path in TMP_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        name = file_path.name.lower()

        if name.endswith(".pdf"):
            return "pdf"
        if name.endswith(".rtf"):
            return "rtf"
        if name.endswith(".exe"):
            return "exe"
        if name.endswith(".doc") or name.endswith(".docx"):
            return "docx"
        if name.endswith(".xls") or name.endswith(".xlsx"):
            return "xlsx"
        if name.endswith(".ppt") or name.endswith(".pptx"):
            return "pptx"

    return "unknown"


def detect_with_exiftool(image_path):
    res = run_cmd(["exiftool", str(image_path)])

    if res is None:
        return "error"

    text = (res.stdout + res.stderr).lower()

    if "pdf" in text:
        return "pdf"
    if "rtf" in text:
        return "rtf"
    if "exe" in text:
        return "exe"
    if "docx" in text:
        return "docx"
    if "xlsx" in text:
        return "xlsx"
    if "pptx" in text:
        return "pptx"

    return "unknown"


def load_ground_truth():
    ground_truth = {}

    with open(GROUND_TRUTH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ground_truth[row["stego_file"]] = row["payload_ext"].lower()

    return ground_truth


def load_my_predictions():
    predictions = {}

    with open(MY_RESULTS, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            pred = row["predicted_label"].lower()

            if "docx" in pred:
                pred = "docx"
            elif "xlsx" in pred:
                pred = "xlsx"
            elif "pptx" in pred:
                pred = "pptx"
            elif "pdf" in pred:
                pred = "pdf"
            elif "rtf" in pred:
                pred = "rtf"
            elif "exe" in pred:
                pred = "exe"
            else:
                pred = "unknown"

            predictions[row["stego_file"]] = pred

    return predictions


def main():
    ground_truth = load_ground_truth()
    my_predictions = load_my_predictions()

    summary = {tool: {"correct": 0, "total": 0} for tool in TOOLS}
    per_file = []

    files = sorted(ground_truth.keys())

    for i, stego_file in enumerate(files, start=1):
        image_path = STEGO_DIR / stego_file
        true_type = ground_truth[stego_file]

        print(f"[{i}/{len(files)}] Processing {stego_file}")

        pred = my_predictions.get(stego_file, "unknown")
        ok = pred == true_type
        summary["my_tool"]["total"] += 1
        summary["my_tool"]["correct"] += int(ok)
        per_file.append([stego_file, true_type, "my_tool", pred, ok])

        pred = detect_with_zsteg(image_path)
        ok = pred == true_type
        summary["zsteg"]["total"] += 1
        summary["zsteg"]["correct"] += int(ok)
        per_file.append([stego_file, true_type, "zsteg", pred, ok])

        pred = detect_with_binwalk(image_path)
        ok = pred == true_type
        summary["binwalk"]["total"] += 1
        summary["binwalk"]["correct"] += int(ok)
        per_file.append([stego_file, true_type, "binwalk", pred, ok])

        pred = detect_with_foremost(image_path)
        ok = pred == true_type
        summary["foremost"]["total"] += 1
        summary["foremost"]["correct"] += int(ok)
        per_file.append([stego_file, true_type, "foremost", pred, ok])

        pred = detect_with_exiftool(image_path)
        ok = pred == true_type
        summary["exiftool"]["total"] += 1
        summary["exiftool"]["correct"] += int(ok)
        per_file.append([stego_file, true_type, "exiftool", pred, ok])

    OUTPUT_PER_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PER_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stego_file", "true_type", "tool", "predicted", "correct"])
        writer.writerows(per_file)

    with open(OUTPUT_SUMMARY, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tool", "correct", "total", "accuracy"])

        for tool in TOOLS:
            correct = summary[tool]["correct"]
            total = summary[tool]["total"]
            acc = (correct / total) * 100 if total else 0
            writer.writerow([tool, correct, total, f"{acc:.2f}%"])

    print("\n=== Comparison complete ===")

    for tool in TOOLS:
        correct = summary[tool]["correct"]
        total = summary[tool]["total"]
        acc = (correct / total) * 100 if total else 0
        print(f"{tool:10s}: {correct}/{total} ({acc:.2f}%)")


if __name__ == "__main__":
    main()