import csv
from pathlib import Path
import sys

root = Path("/home/kali/Desktop/stego_dataset_expanded")
scripts_dir = root / "scripts"
sys.path.insert(0, str(scripts_dir))

from detector_cli import detect_file_type

# ===== INPUT FOLDERS =====
xl_dir = root / "covers_extended_xl"
core_dir = root / "covers_original"   # adjust if different

output_csv = root / "results" / "false_positive_clean_results.csv"

lsb_values = [1, 2, 3]

results = []

total = 0
false_positives = 0

def process_folder(folder, label):
    global total, false_positives

    for img_path in folder.glob("*.*"):
        if img_path.suffix.lower() not in [".bmp", ".png"]:
            continue

        for lsb in lsb_values:
            total += 1

            try:
                predicted = detect_file_type(str(img_path), lsb).strip().upper()

                if predicted == "":
                    predicted = "UNKNOWN"

                is_fp = int(predicted not in ["UNKNOWN", "NONE"])

                if is_fp:
                    false_positives += 1

            except Exception:
                predicted = "ERROR"
                is_fp = 1
                false_positives += 1

            results.append({
                "image": img_path.name,
                "subset": label,
                "lsb": lsb,
                "predicted": predicted,
                "false_positive": is_fp
            })


# Run both datasets
process_folder(xl_dir, "XL")
process_folder(core_dir, "CORE")

# Save CSV
with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

# Summary
print("\n==================== FALSE POSITIVE SUMMARY ====================")
print(f"Total tests       : {total}")
print(f"False positives   : {false_positives}")
print(f"False positive rate : {false_positives / total:.4f}")
print(f"Saved             : {output_csv}")
