import csv
from pathlib import Path
from PIL import Image
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


REPO_ROOT = Path(__file__).resolve().parent.parent

STEGO_DIR = REPO_ROOT / "dataset" / "sample_stego"
GROUND_TRUTH = REPO_ROOT / "dataset" / "ground_truth.csv"
OUTPUT_RESULTS = REPO_ROOT / "results" / "example_outputs" / "detection_results.csv"

MAGIC_BYTES = {
    b"PK\x03\x04": "Office Document (DOCX/XLSX/PPTX)",
    b"%PDF": "PDF Document",
    b"{\\rtf1": "Rich Text Format (RTF)",
    b"MZ": "Windows Executable (EXE)",
}


def get_bytes_in_tag(img, num_lsb):
    num_channels = len(img.getbands())
    max_bits = int(num_channels * img.size[0] * img.size[1] * num_lsb)
    return roundup(max_bits.bit_length() / 8)


def identify_format(data: bytes) -> str:
    """
    Mirrors GUI logic using file signatures and Office internal marker search.
    """
    for sig, name in MAGIC_BYTES.items():
        if data.startswith(sig):
            if sig == b"PK\x03\x04":
                if b"word/" in data:
                    return "DOCX"
                if b"xl/" in data:
                    return "XLSX"
                if b"ppt/" in data:
                    return "PPTX"
                return "ZIP_OR_OFFICE"

            if sig == b"%PDF":
                return "PDF"
            if sig == b"{\\rtf1":
                return "RTF"
            if sig == b"MZ":
                return "EXE"

            return name

    return "UNKNOWN"


def flatten_image_data(img: Image.Image):
    """
    Converts image pixel data into a flat integer list.
    Handles both grayscale and multi-channel images safely.
    """
    pixel_data = list(img.getdata())
    num_channels = len(img.getbands())

    if num_channels == 1:
        return [int(value) for value in pixel_data]

    flat_data = []
    for pixel in pixel_data:
        flat_data.extend(int(channel) for channel in pixel)
    return flat_data


def predict_from_image(image_path: Path, num_lsb: int):
    """
    Returns:
        (predicted_label, tag_size, header_hex8)
    """
    img = Image.open(image_path)
    color_data = flatten_image_data(img)

    tag_size = get_bytes_in_tag(img, num_lsb)

    # Read the tag plus extra bytes to improve Office marker discovery.
    bytes_to_read = tag_size + 5000
    bits_to_read = 8 * bytes_to_read

    max_available_bits = len(color_data) * num_lsb
    if bits_to_read > max_available_bits:
        bits_to_read = max_available_bits

    raw_extracted = lsb_deinterleave_list(color_data, bits_to_read, num_lsb)
    file_header = raw_extracted[tag_size:] if len(raw_extracted) > tag_size else b""

    predicted = identify_format(file_header)
    header_hex8 = file_header[:8].hex(" ") if file_header else ""

    return predicted, tag_size, header_hex8


def map_truth_ext(ext: str) -> str:
    """
    Convert ground-truth payload extensions to detector labels.
    """
    e = ext.strip().lower()

    if e == "docx":
        return "DOCX"
    if e == "xlsx":
        return "XLSX"
    if e == "pptx":
        return "PPTX"
    if e == "pdf":
        return "PDF"
    if e == "rtf":
        return "RTF"
    if e == "exe":
        return "EXE"

    return "UNKNOWN"


def main():
    if not GROUND_TRUTH.exists():
        raise SystemExit(f"Ground truth CSV not found: {GROUND_TRUTH}")

    if not STEGO_DIR.is_dir():
        raise SystemExit(f"Stego directory not found: {STEGO_DIR}")

    rows_out = []
    total = 0
    correct = 0

    by_type = {}
    by_lsb = {}

    with open(GROUND_TRUTH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stego_file = row["stego_file"].strip()
            true_ext = row["payload_ext"].strip()
            lsb = int(row["lsb_n"])

            true_label = map_truth_ext(true_ext)
            image_path = STEGO_DIR / stego_file

            try:
                predicted, tag_size, header_hex8 = predict_from_image(image_path, lsb)
                is_correct = predicted == true_label
                error = ""
            except Exception as exc:
                predicted = "ERROR"
                tag_size = -1
                header_hex8 = ""
                is_correct = False
                error = str(exc)

            total += 1
            correct += int(is_correct)

            by_type.setdefault(true_label, [0, 0])
            by_type[true_label][1] += 1
            if is_correct:
                by_type[true_label][0] += 1

            by_lsb.setdefault(lsb, [0, 0])
            by_lsb[lsb][1] += 1
            if is_correct:
                by_lsb[lsb][0] += 1

            rows_out.append([
                stego_file,
                true_ext,
                true_label,
                lsb,
                predicted,
                is_correct,
                tag_size,
                header_hex8,
                error
            ])

    acc = (correct / total * 100) if total else 0.0

    OUTPUT_RESULTS.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_RESULTS, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "stego_file",
            "payload_ext",
            "true_label",
            "lsb_n",
            "predicted_label",
            "correct",
            "tag_size_bytes",
            "header_hex_8bytes",
            "error"
        ])
        writer.writerows(rows_out)

    print("\n=== Evaluation complete ===")
    print(f"Total samples: {total}")
    print(f"Correct      : {correct}")
    print(f"Accuracy     : {acc:.2f}%")
    print(f"Saved CSV    : {OUTPUT_RESULTS}")

    print("\n--- Accuracy by TRUE type ---")
    for true_type, (c, n) in sorted(by_type.items()):
        print(f"{true_type:6s}: {c}/{n} ({(c / n * 100 if n else 0):.2f}%)")

    print("\n--- Accuracy by LSB depth ---")
    for lsb_depth, (c, n) in sorted(by_lsb.items()):
        print(f"LSB {lsb_depth}: {c}/{n} ({(c / n * 100 if n else 0):.2f}%)")


if __name__ == "__main__":
    main()