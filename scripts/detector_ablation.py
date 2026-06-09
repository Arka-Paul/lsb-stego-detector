from PIL import Image
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup
import sys


MAGIC_BYTES = {
    b"PK\x03\x04": "OFFICE",
    b"%PDF": "PDF",
    b"{\\rtf1": "RTF",
    b"MZ": "EXE",
}


def flatten_image_data(img: Image.Image):
    """
    Convert image pixel data into a flat integer list.
    Handles grayscale and multi-channel images.
    """
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


def identify_format_robust(data: bytes, use_markers: bool = True) -> str:
    """
    Robust signature matching.
    Searches within the first 32 bytes rather than strict startswith(),
    which tolerates small alignment artefacts such as a leading 00 byte.
    """
    header_window = data[:32]

    for signature, format_name in MAGIC_BYTES.items():
        if signature in header_window:
            if signature == b"PK\x03\x04":
                if use_markers:
                    if b"word/" in data:
                        return "DOCX"
                    if b"xl/" in data:
                        return "XLSX"
                    if b"ppt/" in data:
                        return "PPTX"
                return "ZIP"
            return format_name

    return "UNKNOWN"


def pack_bits_to_bytes(bit_list):
    """
    Convert a list of bits into bytes (8 bits per byte).
    """
    out = bytearray()

    usable_len = (len(bit_list) // 8) * 8
    for i in range(0, usable_len, 8):
        byte_val = 0
        for bit in bit_list[i:i+8]:
            byte_val = (byte_val << 1) | bit
        out.append(byte_val)

    return bytes(out)


def naive_sequential_extract(color_data, lsb, bits_to_read):
    """
    Ablation mode: without deinterleaving.
    Still reads LSB payload bits from pixel values, but reconstructs them
    using a naive sequential bit grab instead of the proper StegoLSB
    deinterleaving routine.

    This is technically a much better ablation than reading the raw image
    file bytes, because it still operates in the stego bit domain.
    """
    bits = []

    for value in color_data:
        # naive bit access: collect LSB planes directly in sequential order
        for bit_pos in range(lsb):
            bits.append((value >> bit_pos) & 1)
            if len(bits) >= bits_to_read:
                return pack_bits_to_bytes(bits)

    return pack_bits_to_bytes(bits)


def detect_file_type(image_path: str, lsb: int, mode: str) -> str:
    """
    Supported modes:
    - full
    - no_deinterleaving
    - no_buffer
    - no_markers
    """
    img = Image.open(image_path)
    color_data, num_channels, width, height = flatten_image_data(img)

    max_bits = num_channels * width * height * lsb
    tag_size = roundup(max_bits.bit_length() / 8)

    # Full method uses a large buffer to reach deeper internal markers
    if mode == "no_buffer":
        bytes_to_read = tag_size + 32
    else:
        bytes_to_read = tag_size + 10000

    bits_to_read = 8 * bytes_to_read
    max_available_bits = len(color_data) * lsb

    if bits_to_read > max_available_bits:
        bits_to_read = max_available_bits

    if bits_to_read <= 0:
        return "UNKNOWN"

    # --- Ablation: without deinterleaving ---
    if mode == "no_deinterleaving":
        raw_extracted = naive_sequential_extract(color_data, lsb, bits_to_read)
    else:
        raw_extracted = lsb_deinterleave_list(color_data, bits_to_read, lsb)

    # Keep tag removal active for these tutor-requested ablations.
    file_data = raw_extracted[tag_size:] if len(raw_extracted) > tag_size else b""

    # --- Ablation: without internal markers ---
    if mode == "no_markers":
        return identify_format_robust(file_data, use_markers=False)

    return identify_format_robust(file_data, use_markers=True)


def main():
    if len(sys.argv) != 4:
        print("Usage: python detector_ablation.py <image_path> <lsb> <mode>", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    lsb = int(sys.argv[2])
    mode = sys.argv[3].strip().lower()

    valid_modes = {"full", "no_deinterleaving", "no_buffer", "no_markers"}
    if mode not in valid_modes:
        print("ERROR")
        sys.exit(1)

    try:
        result = detect_file_type(image_path, lsb, mode)
        print(result)
    except Exception:
        print("ERROR")


if __name__ == "__main__":
    main()
