import csv
from pathlib import Path

root = Path("/home/kali/Desktop/stego_dataset_expanded")
input_csv = root / "results" / "detection_results_expanded.csv"
output_csv = root / "results" / "confusion_matrix.csv"

labels = ["PDF", "DOCX", "XLSX", "PPTX", "RTF", "EXE"]

matrix = {actual: {pred: 0 for pred in labels} for actual in labels}

with input_csv.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        actual = row["expected_type"].strip().upper()
        predicted = row["predicted_type"].strip().upper()

        if actual in labels and predicted in labels:
            matrix[actual][predicted] += 1

with output_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Actual \\ Predicted"] + labels)

    for actual in labels:
        writer.writerow([actual] + [matrix[actual][pred] for pred in labels])

print(f"Saved: {output_csv}")
for actual in labels:
    print(actual, matrix[actual])
