import csv
import time
from pathlib import Path
import sys

root = Path("/home/kali/Desktop/stego_dataset_expanded")
scripts_dir = root / "scripts"
sys.path.insert(0, str(scripts_dir))

# This should point to the CLI wrapper built from your tool's logic
from detector_cli import detect_file_type

manifest = root / "results" / "stego_manifest_combined.csv"
output_per_file = root / "results" / "runtime_per_file.csv"
output_summary = root / "results" / "runtime_summary.csv"

rows = []

total_images = 0
correct_count = 0
incorrect_count = 0
total_runtime = 0.0

fastest = None
slowest = None

with manifest.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for i, row in enumerate(reader, start=1):
        stego_filename = row["stego_filename"]
        stego_path = row["stego_path"]
        lsb = int(row["lsb"])
        expected = row["expected_type"].strip().upper()

        start = time.perf_counter()

        try:
            predicted = detect_file_type(stego_path, lsb).strip().upper()
            if predicted == "":
                predicted = "UNKNOWN"
            status = "ok"
        except Exception as e:
            predicted = "ERROR"
            status = "error"

        end = time.perf_counter()
        runtime_sec = end - start

        correct = int(predicted == expected)

        total_images += 1
        total_runtime += runtime_sec
        correct_count += correct
        incorrect_count += int(not correct)

        row_out = {
            "stego_filename": stego_filename,
            "subset": row["subset"],
            "cover_filename": row["cover_filename"],
            "cover_category": row["cover_category"],
            "cover_size_label": row["cover_size_label"],
            "cover_format": row["cover_format"],
            "payload_filename": row["payload_filename"],
            "payload_type": row["payload_type"].upper(),
            "payload_size_class": row["payload_size_class"],
            "lsb": lsb,
            "expected_type": expected,
            "predicted_type": predicted,
            "correct": correct,
            "status": status,
            "runtime_seconds": f"{runtime_sec:.6f}"
        }

        rows.append(row_out)

        # fastest/slowest among successful detections only
        if status == "ok" and correct == 1:
            if fastest is None or runtime_sec < fastest["runtime"]:
                fastest = {
                    "filename": stego_filename,
                    "runtime": runtime_sec,
                    "payload_type": row["payload_type"].upper(),
                    "lsb": lsb,
                    "subset": row["subset"]
                }

            if slowest is None or runtime_sec > slowest["runtime"]:
                slowest = {
                    "filename": stego_filename,
                    "runtime": runtime_sec,
                    "payload_type": row["payload_type"].upper(),
                    "lsb": lsb,
                    "subset": row["subset"]
                }

        if i % 100 == 0:
            print(f"Processed {i} images...")

# Save per-file runtime log
with output_per_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

average_runtime = total_runtime / total_images if total_images else 0.0

# Save summary
with output_summary.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["metric", "value"])
    writer.writerow(["total_images", total_images])
    writer.writerow(["correct_detections", correct_count])
    writer.writerow(["incorrect_detections", incorrect_count])
    writer.writerow(["total_runtime_seconds", f"{total_runtime:.6f}"])
    writer.writerow(["average_runtime_per_image_seconds", f"{average_runtime:.6f}"])

    if fastest:
        writer.writerow(["fastest_successful_image", fastest["filename"]])
        writer.writerow(["fastest_successful_runtime_seconds", f"{fastest['runtime']:.6f}"])
        writer.writerow(["fastest_successful_payload_type", fastest["payload_type"]])
        writer.writerow(["fastest_successful_lsb", fastest["lsb"]])
        writer.writerow(["fastest_successful_subset", fastest["subset"]])

    if slowest:
        writer.writerow(["slowest_successful_image", slowest["filename"]])
        writer.writerow(["slowest_successful_runtime_seconds", f"{slowest['runtime']:.6f}"])
        writer.writerow(["slowest_successful_payload_type", slowest["payload_type"]])
        writer.writerow(["slowest_successful_lsb", slowest["lsb"]])
        writer.writerow(["slowest_successful_subset", slowest["subset"]])

print("\n==================== RUNTIME SUMMARY ====================")
print(f"Total images processed              : {total_images}")
print(f"Correct detections                  : {correct_count}")
print(f"Incorrect detections                : {incorrect_count}")
print(f"Total runtime (s)                   : {total_runtime:.6f}")
print(f"Average runtime per image (s)       : {average_runtime:.6f}")

if fastest:
    print(f"Fastest successful image            : {fastest['filename']}")
    print(f"Fastest successful runtime (s)      : {fastest['runtime']:.6f}")
    print(f"Fastest successful payload / LSB    : {fastest['payload_type']} / {fastest['lsb']}")
    print(f"Fastest successful subset           : {fastest['subset']}")

if slowest:
    print(f"Slowest successful image            : {slowest['filename']}")
    print(f"Slowest successful runtime (s)      : {slowest['runtime']:.6f}")
    print(f"Slowest successful payload / LSB    : {slowest['payload_type']} / {slowest['lsb']}")
    print(f"Slowest successful subset           : {slowest['subset']}")

print(f"\nSaved per-file runtime log          : {output_per_file}")
print(f"Saved runtime summary               : {output_summary}")
