import csv
import hashlib
from pathlib import Path
from PIL import Image

ROOT = Path("/home/kali/Desktop/stego_dataset_expanded")

PAYLOAD_ROOT = ROOT / "payload_bank"
COVER_DIRS = [
    ROOT / "covers_original",
    ROOT / "covers_extended_xl",
]

RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

PAYLOAD_OUT = RESULTS / "payload_sizes_and_hashes.csv"
COVER_OUT = RESULTS / "cover_dimensions_and_modes.csv"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_payload_metadata():
    rows = []

    for path in sorted(PAYLOAD_ROOT.rglob("*")):
        if not path.is_file():
            continue

        rel = path.relative_to(PAYLOAD_ROOT)
        parts = rel.parts

        if len(parts) >= 3:
            payload_type = parts[0]
            size_class = parts[1]
        else:
            payload_type = path.suffix.lower().lstrip(".")
            size_class = "unknown"

        rows.append({
            "payload_type": payload_type.upper(),
            "size_class": size_class,
            "filename": path.name,
            "relative_path": str(rel),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    with PAYLOAD_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "payload_type",
                "size_class",
                "filename",
                "relative_path",
                "size_bytes",
                "sha256",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved payload metadata: {PAYLOAD_OUT}")


def write_cover_metadata():
    rows = []

    for cover_dir in COVER_DIRS:
        if not cover_dir.exists():
            print(f"Warning: missing cover directory: {cover_dir}")
            continue

        subset = cover_dir.name

        for path in sorted(cover_dir.glob("*")):
            if path.suffix.lower() not in {".png", ".bmp"}:
                continue

            try:
                with Image.open(path) as img:
                    width, height = img.size
                    mode = img.mode
                    bands = "".join(img.getbands())
                    channel_count = len(img.getbands())

                rows.append({
                    "subset": subset,
                    "filename": path.name,
                    "relative_path": str(path.relative_to(ROOT)),
                    "format": path.suffix.lower().lstrip(".").upper(),
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "bands": bands,
                    "channel_count": channel_count,
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                })

            except Exception as exc:
                rows.append({
                    "subset": subset,
                    "filename": path.name,
                    "relative_path": str(path.relative_to(ROOT)),
                    "format": path.suffix.lower().lstrip(".").upper(),
                    "width": "ERROR",
                    "height": "ERROR",
                    "mode": "ERROR",
                    "bands": "ERROR",
                    "channel_count": "ERROR",
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "error": str(exc),
                })

    with COVER_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "subset",
                "filename",
                "relative_path",
                "format",
                "width",
                "height",
                "mode",
                "bands",
                "channel_count",
                "size_bytes",
                "sha256",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved cover metadata: {COVER_OUT}")


if __name__ == "__main__":
    write_payload_metadata()
    write_cover_metadata()
