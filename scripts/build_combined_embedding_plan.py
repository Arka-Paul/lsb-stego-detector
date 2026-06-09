from pathlib import Path
from PIL import Image
import csv

root = Path("/home/kali/Desktop/stego_dataset_expanded")
original_dir = root / "covers_original"
xl_dir = root / "covers_extended_xl"
payload_bank = root / "payload_bank"
out_csv = root / "results" / "embedding_plan_combined.csv"

def infer_channels(mode: str) -> int:
    if mode == "RGB":
        return 3
    if mode == "RGBA":
        return 4
    if mode == "L":
        return 1
    return 0

def parse_original_cover_name(filename: str):
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) != 3:
        raise ValueError(f"Unexpected original cover filename format: {filename}")
    category, variant, size_label = parts
    return {
        "subset": "core",
        "cover_category": category,
        "cover_variant": variant,
        "cover_size_label": size_label,
    }

def parse_xl_cover_name(filename: str):
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) != 3:
        raise ValueError(f"Unexpected XL cover filename format: {filename}")
    category, variant, fmt_tag = parts
    return {
        "subset": "extended_xl",
        "cover_category": category,
        "cover_variant": variant,
        "cover_size_label": fmt_tag,
    }

def parse_payload_path(p: Path):
    filetype = p.parent.parent.name
    size_class = p.parent.name
    filename = p.name
    size_bytes = p.stat().st_size
    return filetype, size_class, filename, size_bytes

rows = []
payload_files = sorted([p for p in payload_bank.rglob("*") if p.is_file()])

cover_files = []
cover_files.extend(sorted([p for p in original_dir.iterdir() if p.is_file()]))
cover_files.extend(sorted([p for p in xl_dir.iterdir() if p.is_file()]))

for cover in cover_files:
    if cover.parent.name == "covers_original":
        meta = parse_original_cover_name(cover.name)
    else:
        meta = parse_xl_cover_name(cover.name)

    with Image.open(cover) as img:
        mode = img.mode
        width, height = img.size

    channels = infer_channels(mode)
    total_slots = width * height * channels
    is_grayscale_png = int(mode == "L" and cover.suffix.lower() == ".png")

    for payload in payload_files:
        payload_type, payload_size_class, payload_filename, payload_size_bytes = parse_payload_path(payload)

        for lsb in [1, 2, 3]:
            capacity_bytes = (total_slots * lsb) // 8

            if is_grayscale_png:
                status = "SKIP_TOOL_LIMITATION"
                reason = "StegoLSB grayscale PNG iterable pixel failure"
            elif payload_size_bytes > capacity_bytes:
                status = "SKIP_CAPACITY"
                reason = "Payload exceeds cover capacity at selected LSB depth"
            else:
                status = "OK"
                reason = ""

            rows.append({
                "subset": meta["subset"],
                "cover_filename": cover.name,
                "cover_category": meta["cover_category"],
                "cover_variant": meta["cover_variant"],
                "cover_size_label": meta["cover_size_label"],
                "cover_format": cover.suffix.lower().lstrip("."),
                "cover_mode": mode,
                "cover_width": width,
                "cover_height": height,
                "cover_channels": channels,
                "payload_filename": payload_filename,
                "payload_type": payload_type,
                "payload_size_class": payload_size_class,
                "payload_size_bytes": payload_size_bytes,
                "lsb": lsb,
                "capacity_bytes": capacity_bytes,
                "status": status,
                "reason": reason,
            })

fieldnames = list(rows[0].keys())

with out_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {out_csv}")
print(f"Total rows: {len(rows)}")

ok = sum(r["status"] == "OK" for r in rows)
cap = sum(r["status"] == "SKIP_CAPACITY" for r in rows)
tool = sum(r["status"] == "SKIP_TOOL_LIMITATION" for r in rows)

print(f"OK: {ok}")
print(f"SKIP_CAPACITY: {cap}")
print(f"SKIP_TOOL_LIMITATION: {tool}")
