import csv
from pathlib import Path
from collections import defaultdict

root = Path("/home/kali/Desktop/stego_dataset_expanded")
input_csv = root / "results" / "detection_results_expanded.csv"
output_csv = root / "results" / "false_positive_analysis.csv"

labels = ["PDF", "DOCX", "XLSX", "PPTX", "RTF", "EXE"]

false_positive = defaultdict(int)
total_predicted = defaultdict(int)

with input_csv.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        actual = row["expected_type"].strip().upper()
        predicted = row["predicted_type"].strip().upper()

        total_predicted[predicted] += 1

        if actual != predicted:
            false_positive[predicted] += 1

rows = []
for label in labels:
    total = total_predicted[label]
    fp = false_positive[label]
    rate = (fp / total * 100) if total else 0.0

    rows.append({
        "type": label,
        "total_predictions": total,
        "false_positives": fp,
        "false_positive_rate": f"{rate:.2f}"
    })

with output_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["type", "total_predictions", "false_positives", "false_positive_rate"]
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {output_csv}")
for r in rows:
    print(r)
