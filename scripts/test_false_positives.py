import csv
from pathlib import Path
from PIL import Image
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


REPO_ROOT = Path(__file__).resolve().parent.parent

CLEAN_DIR = REPO_ROOT / "dataset" / "sample_covers"
OUTPUT = REPO_ROOT / "results" / "example_outputs" / "false_positive_results.csv"

MAGIC_BYTES = {
    b"PK\x03\x04": "Office Document",
    b"%PDF": "PDF Document",
    b"{\\rtf1": "RTF",
    b"MZ": "EXE",
}


def get_bytes_in_tag(img, num_lsb):
    num_channels = len(img.getbands())
    max_bits = int(num_channels * img.size[0] * img.size[1] * num_lsb)
    return roundup(max_bits.bit_length() / 8)


def identify_format(data):
    for sig, name in MAGIC_BYTES.items():
        if data.startswith(sig):
            if sig == b"PK\x03\x04":
                if b"word/" in data:
                    return "DOCX"
                if b"xl/" in data:
                    return "XLSX"
                if b"ppt/" in data:
                    return "PPTX"
                return "ZIP"

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


def main():
    if not CLEAN_DIR.is_dir():
        raise SystemExit(f"Clean image directory not found: {CLEAN_DIR}")

    rows = []
    false_positives = 0
    total_tests = 0
    errors = 0

    images = sorted([p for p in CLEAN_DIR.iterdir() if p.is_file()])

    for image_path in images:
        img_file = image_path.name

        for lsb in [1, 2, 3]:
            try:
                img = Image.open(image_path)
                color_data = flatten_image_data(img)

                tag_size = get_bytes_in_tag(img, lsb)
                bytes_to_read = tag_size + 5000
                bits_to_read = 8 * bytes_to_read

                max_available_bits = len(color_data) * lsb
                if bits_to_read > max_available_bits:
                    bits_to_read = max_available_bits

                raw = lsb_deinterleave_list(color_data, bits_to_read, lsb)
                header = raw[tag_size:] if len(raw) > tag_size else b""

                detected = identify_format(header)
                is_fp = detected != "UNKNOWN"

                if is_fp:
                    false_positives += 1

                total_tests += 1

                rows.append([
                    img_file,
                    lsb,
                    detected,
                    is_fp,
                    ""
                ])

            except Exception as exc:
                total_tests += 1
                errors += 1

                rows.append([
                    img_file,
                    lsb,
                    "ERROR",
                    False,
                    str(exc)
                ])

    false_positive_rate = (false_positives / total_tests) * 100 if total_tests else 0.0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image",
            "lsb",
            "detected_type",
            "false_positive",
            "error"
        ])
        writer.writerows(rows)

    print("\nFalse Positive Test Complete")
    print(f"Total tests        : {total_tests}")
    print(f"False positives    : {false_positives}")
    print(f"Errors             : {errors}")
    print(f"False positive rate: {false_positive_rate:.2f}%")
    print(f"Results saved to   : {OUTPUT}")


if __name__ == "__main__":
    main()