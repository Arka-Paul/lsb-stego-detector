import csv
from pathlib import Path
import sys

root = Path("/home/kali/Desktop/stego_dataset_expanded")
scripts_dir = root / "scripts"
sys.path.insert(0, str(scripts_dir))

from detector_ablation import detect_file_type

manifest = root / "results" / "stego_manifest_combined.csv"
output_per_file = root / "results" / "ablation_results_per_file.csv"
output_summary = root / "results" / "ablation_results_summary.csv"

modes = ["full", "no_deinterleaving", "no_buffer", "no_markers"]

summary = {mode: {"correct": 0, "total": 0} for mode in modes}
rows = []

with manifest.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader, start=1):
        stego_path = row["stego_path"]
        lsb = int(row["lsb"])
        expected = row["expected_type"].strip().upper()

        if i % 100 == 0:
            print(f"Processed {i} images...")

        for mode in modes:
            try:
                predicted = detect_file_type(stego_path, lsb, mode).strip().upper()
                if predicted == "":
                    predicted = "UNKNOWN"
            except Exception:
                predicted = "ERROR"

            # ZIP counts as incorrect for DOCX/XLSX/PPTX subtype attribution
            correct = int(predicted == expected)

            summary[mode]["total"] += 1
            summary[mode]["correct"] += correct

            rows.append({
                "stego_filename": row["stego_filename"],
                "subset": row["subset"],
                "expected_type": expected,
                "payload_type": row["payload_type"].upper(),
                "payload_size_class": row["payload_size_class"],
                "lsb": lsb,
                "mode": mode,
                "predicted_type": predicted,
                "correct": correct
            })

# Save per-file results
with output_per_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "stego_filename",
            "subset",
            "expected_type",
            "payload_type",
            "payload_size_class",
            "lsb",
            "mode",
            "predicted_type",
            "correct"
        ]
    )
    writer.writeheader()
    writer.writerows(rows)

# Save summary
summary_rows = []
with output_summary.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["configuration", "correct", "total", "accuracy_percent"])

    for mode in modes:
        c = summary[mode]["correct"]
        t = summary[mode]["total"]
        acc = (c / t) * 100 if t else 0.0

        summary_rows.append([mode, c, t, f"{acc:.2f}"])
        writer.writerow([mode, c, t, f"{acc:.2f}"])

print("\n==================== ABLATION SUMMARY ====================")
for mode, c, t, acc in summary_rows:
    print(f"{mode:20s}: {c}/{t} ({acc}%)")

print(f"\nSaved per-file results : {output_per_file}")
print(f"Saved summary results  : {output_summary}")
