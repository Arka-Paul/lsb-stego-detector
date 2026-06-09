import csv
from pathlib import Path
import sys

root = Path("/home/kali/Desktop/stego_dataset_expanded")
scripts_dir = root / "scripts"
sys.path.insert(0, str(scripts_dir))

from detector_cli import detect_file_type

manifest = root / "results" / "stego_manifest_combined.csv"
output_csv = root / "results" / "detection_results_combined.csv"

results = []

total = 0
correct_count = 0
incorrect_count = 0

with manifest.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        total += 1

        stego_path = row["stego_path"]
        lsb = int(row["lsb"])
        expected = row["expected_type"].strip().upper()

        try:
            predicted = detect_file_type(stego_path, lsb).strip().upper()

            if predicted == "":
                predicted = "UNKNOWN"

            correct = int(predicted == expected)

            if correct:
                correct_count += 1
            else:
                incorrect_count += 1

        except Exception:
            predicted = "ERROR"
            correct = 0
            incorrect_count += 1

        results.append({
            **row,
            "predicted_type": predicted,
            "correct": correct
        })

fieldnames = list(results[0].keys())

with output_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print("\n==================== DETECTION SUMMARY ====================")
print(f"Total samples : {total}")
print(f"Correct       : {correct_count}")
print(f"Incorrect     : {incorrect_count}")
print(f"Accuracy      : {correct_count / total:.4f}")
print(f"Saved         : {output_csv}")
