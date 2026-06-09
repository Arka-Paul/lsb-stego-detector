from pathlib import Path
import csv

root = Path("/home/kali/Desktop/stego_dataset_expanded")
success_log = root / "logs" / "embedding_success_combined.csv"
out_csv = root / "results" / "stego_manifest_combined.csv"

rows = []

with success_log.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        subset = row["subset"]
        cover_filename = row["cover_filename"]
        payload_filename = row["payload_filename"]
        payload_type = row["payload_type"]
        payload_size_class = row["payload_size_class"]
        lsb = int(row["lsb"])
        output_file = row["output_file"]

        stem = Path(cover_filename).stem
        parts = stem.split("_")

        if subset == "core":
            if len(parts) != 3:
                raise ValueError(f"Unexpected core cover filename format: {cover_filename}")
            cover_category, cover_variant, cover_size_label = parts
        elif subset == "extended_xl":
            if len(parts) != 3:
                raise ValueError(f"Unexpected XL cover filename format: {cover_filename}")
            cover_category, cover_variant, cover_size_label = parts
        else:
            raise ValueError(f"Unknown subset: {subset}")

        cover_format = Path(cover_filename).suffix.lower().lstrip(".")

        rows.append({
            "subset": subset,
            "stego_filename": Path(output_file).name,
            "stego_path": output_file,
            "cover_filename": cover_filename,
            "cover_category": cover_category,
            "cover_variant": cover_variant,
            "cover_size_label": cover_size_label,
            "cover_format": cover_format,
            "payload_filename": payload_filename,
            "payload_type": payload_type,
            "payload_size_class": payload_size_class,
            "lsb": lsb,
            "expected_type": payload_type.upper(),
        })

fieldnames = [
    "subset",
    "stego_filename",
    "stego_path",
    "cover_filename",
    "cover_category",
    "cover_variant",
    "cover_size_label",
    "cover_format",
    "payload_filename",
    "payload_type",
    "payload_size_class",
    "lsb",
    "expected_type",
]

with out_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {out_csv}")
print(f"Rows: {len(rows)}")
