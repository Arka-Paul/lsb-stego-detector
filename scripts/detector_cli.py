from pathlib import Path
from PIL import Image
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup
import sys


MAGIC_BYTES = {
    b"PK\x03\x04": "Office Document (DOCX/XLSX/PPTX)",
    b"%PDF": "PDF Document",
    b"{\\rtf1": "Rich Text Format (RTF)",
    b"MZ": "Windows Executable (EXE)",
}


def identify_format(data: bytes) -> str:
    for signature, format_name in MAGIC_BYTES.items():
        if data.startswith(signature):
            if signature == b"PK\x03\x04":
                if b"word/" in data:
                    return "DOCX"
                if b"xl/" in data:
                    return "XLSX"
                if b"ppt/" in data:
                    return "PPTX"
                return "ZIP"
            if signature == b"%PDF":
                return "PDF"
            if signature == b"{\\rtf1":
                return "RTF"
            if signature == b"MZ":
                return "EXE"
    return "UNKNOWN"


def flatten_image_data(img: Image.Image):
    width, height = img.size
    bands = img.getbands()
    num_channels = len(bands)

    pixel_data = list(img.getdata())
    flat_data = []

    if num_channels == 1:
        flat_data = [int(value) for value in pixel_data]
    else:
        for pixel in pixel_data:
            flat_data.extend(int(channel) for channel in pixel)

    return flat_data, num_channels, width, height


def detect_file_type(image_path: str, lsb: int) -> str:
    img = Image.open(image_path)
    color_data, num_channels, width, height = flatten_image_data(img)

    max_bits = num_channels * width * height * lsb
    tag_size = roundup(max_bits.bit_length() / 8)

    bytes_to_read = tag_size + 10000
    bits_to_read = 8 * bytes_to_read

    max_available_bits = len(color_data) * lsb
    if bits_to_read > max_available_bits:
        bits_to_read = max_available_bits

    if bits_to_read <= 0:
        return "UNKNOWN"

    raw_extracted = lsb_deinterleave_list(
        color_data,
        bits_to_read,
        lsb
    )

    file_header = raw_extracted[tag_size:] if len(raw_extracted) > tag_size else b""
    detected_format = identify_format(file_header)
    return detected_format


def main():
    if len(sys.argv) != 3:
        print("Usage: python detector_cli.py <image_path> <lsb>", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    lsb = int(sys.argv[2])

    try:
        result = detect_file_type(image_path, lsb)
        print(result)
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
