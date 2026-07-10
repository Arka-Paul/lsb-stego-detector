from pathlib import Path
from PIL import Image
import argparse
import csv
import io
import re
import time
import zipfile
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


UNKNOWN = "Unknown/None"

PAYLOAD_MAP = {
    "pdf": "PDF",
    "docx": "DOCX",
    "xlsx": "XLSX",
    "pptx": "PPTX",
    "rtf": "RTF",
    "exe": "EXE",
}


def flatten_image_data(img: Image.Image) -> tuple[list[int], int, int, int]:
    width, height = img.size
    bands = img.getbands()
    num_channels = len(bands)

    pixel_data = list(img.getdata())
    flat_data: list[int] = []

    if num_channels == 1:
        flat_data = [int(value) for value in pixel_data]
    else:
        for pixel in pixel_data:
            flat_data.extend(int(channel) for channel in pixel)

    return flat_data, num_channels, width, height


def matches_known_signature(data: bytes) -> bool:
    return (
        data.startswith(b"PK\x03\x04")
        or data.startswith(b"%PDF")
        or data.startswith(b"{\\rtf1")
        or data.startswith(b"MZ")
    )


def identify_format(data: bytes) -> tuple[str, str]:
    """
    Returns:
    detected_type, validation_status

    detected_type is one of:
    DOCX, XLSX, PPTX, PDF, RTF, EXE, Unknown/None
    """

    if not data:
        return UNKNOWN, "empty_payload"

    # 1. Office Open XML / ZIP structural validation
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                bad_file = zf.testzip()
                if bad_file is not None:
                    return UNKNOWN, f"zip_crc_failed:{bad_file}"

                namelist = zf.namelist()

                if "[Content_Types].xml" not in namelist:
                    return UNKNOWN, "zip_missing_content_types"

                if any(name.startswith("word/") for name in namelist):
                    return "DOCX", "validated_ooxml_docx"

                if any(name.startswith("xl/") for name in namelist):
                    return "XLSX", "validated_ooxml_xlsx"

                if any(name.startswith("ppt/") for name in namelist):
                    return "PPTX", "validated_ooxml_pptx"

                return UNKNOWN, "zip_valid_but_not_ooxml_target"

        except (
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
            RuntimeError,
            ValueError,
            NotImplementedError,
            OSError,
        ) as exc:
            return UNKNOWN, f"zip_validation_failed:{type(exc).__name__}"

    # 2. PDF structural validation
    if data.startswith(b"%PDF"):
        if b"startxref" in data and b"%%EOF" in data[-8192:]:
            return "PDF", "validated_pdf_startxref_eof"
        return UNKNOWN, "pdf_missing_startxref_or_eof"

    # 3. Windows PE executable validation
    if data.startswith(b"MZ"):
        if len(data) >= 0x40:
            pe_offset = int.from_bytes(data[0x3C:0x40], byteorder="little")
            if 0 < pe_offset < len(data) - 4:
                if data[pe_offset:pe_offset + 4] == b"PE\x00\x00":
                    return "EXE", "validated_mz_pe_header"
        return UNKNOWN, "mz_missing_valid_pe_header"

    # 4. RTF structural validation
    if data.startswith(b"{\\rtf1"):
        head = data[:512]
        if b"\\ansi" in head or b"\\deff" in head or data.rstrip().endswith(b"}"):
            return "RTF", "validated_rtf_structure"
        return UNKNOWN, "rtf_weak_structure"

    return UNKNOWN, "no_known_signature"


def decode_candidate_lengths(
    tag_bytes: bytes,
    tag_size: int,
    max_available_bytes: int
) -> list[tuple[str, int]]:
    """
    Decodes plausible payload lengths from the stego-lsb size tag.
    Big-endian is tried first, with little-endian retained as fallback.
    """

    candidate_lengths: list[tuple[str, int]] = []

    for endian in ("big", "little"):
        payload_length = int.from_bytes(tag_bytes[:tag_size], byteorder=endian)

        if 0 < payload_length <= (max_available_bytes - tag_size):
            candidate_lengths.append((endian, payload_length))

    unique_candidates: list[tuple[str, int]] = []
    seen_lengths: set[int] = set()

    for endian, length in candidate_lengths:
        if length not in seen_lengths:
            unique_candidates.append((endian, length))
            seen_lengths.add(length)

    return unique_candidates


def infer_expected_from_filename(path: Path) -> tuple[str, int]:
    """
    Expected filename examples:
    Flat-Color_1_S__docx_small__lsb1.bmp
    Flat-Color_1_S__pdf_small__lsb2.bmp
    """

    name = path.name.lower()

    expected_type = ""
    for key, value in PAYLOAD_MAP.items():
        if f"__{key}_" in name or f"_{key}_" in name:
            expected_type = value
            break

    match = re.search(r"lsb([123])", name)
    expected_lsb = int(match.group(1)) if match else -1

    return expected_type, expected_lsb


def detect_one(path: Path, lsb: int) -> dict:
    try:
        with Image.open(path) as img:
            color_data, num_channels, width, height = flatten_image_data(img)

        max_bits = num_channels * width * height * lsb
        tag_size = roundup(max_bits.bit_length() / 8)

        max_available_bits = len(color_data) * lsb
        max_available_bytes = max_available_bits // 8

        tag_bits_to_read = min(8 * tag_size, max_available_bits)

        if tag_bits_to_read <= 0:
            return {
                "detected_type": UNKNOWN,
                "validation_status": "no_data",
                "tag_size": tag_size,
                "payload_length": "",
                "tag_endian": "",
                "header_hex": "",
                "error": "",
            }

        tag_bytes = lsb_deinterleave_list(
            color_data,
            tag_bits_to_read,
            lsb
        )

        if len(tag_bytes) < tag_size:
            return {
                "detected_type": UNKNOWN,
                "validation_status": "incomplete_tag",
                "tag_size": tag_size,
                "payload_length": "",
                "tag_endian": "",
                "header_hex": tag_bytes[:8].hex(" "),
                "error": "",
            }

        candidate_lengths = decode_candidate_lengths(
            tag_bytes=tag_bytes,
            tag_size=tag_size,
            max_available_bytes=max_available_bytes,
        )

        if not candidate_lengths:
            return {
                "detected_type": UNKNOWN,
                "validation_status": "no_plausible_payload_length",
                "tag_size": tag_size,
                "payload_length": "",
                "tag_endian": "",
                "header_hex": tag_bytes[:8].hex(" "),
                "error": "",
            }

        first_header = b""

        for endian, payload_length in candidate_lengths:
            # First read only a short prefix.
            prefix_bytes_to_read = tag_size + min(payload_length, 16)
            prefix_bits_to_read = min(
                8 * prefix_bytes_to_read,
                max_available_bits
            )

            raw_prefix = lsb_deinterleave_list(
                color_data,
                prefix_bits_to_read,
                lsb
            )

            candidate_prefix = raw_prefix[tag_size:tag_size + 16]

            if not first_header:
                first_header = candidate_prefix

            # If no known signature appears, avoid full extraction.
            if not matches_known_signature(candidate_prefix):
                continue

            # Extract full payload candidate for structural validation.
            full_bytes_to_read = tag_size + payload_length
            full_bits_to_read = min(
                8 * full_bytes_to_read,
                max_available_bits
            )

            raw_extracted = lsb_deinterleave_list(
                color_data,
                full_bits_to_read,
                lsb
            )

            candidate_payload = raw_extracted[
                tag_size:tag_size + payload_length
            ]

            detected_type, validation_status = identify_format(candidate_payload)

            if detected_type != UNKNOWN:
                return {
                    "detected_type": detected_type,
                    "validation_status": validation_status,
                    "tag_size": tag_size,
                    "payload_length": payload_length,
                    "tag_endian": endian,
                    "header_hex": candidate_payload[:8].hex(" "),
                    "error": "",
                }

        return {
            "detected_type": UNKNOWN,
            "validation_status": "signature_or_structure_not_valid",
            "tag_size": tag_size,
            "payload_length": candidate_lengths[0][1] if candidate_lengths else "",
            "tag_endian": candidate_lengths[0][0] if candidate_lengths else "",
            "header_hex": first_header[:8].hex(" ") if first_header else "",
            "error": "",
        }

    except Exception as exc:
        return {
            "detected_type": "Processing Failed",
            "validation_status": "error",
            "tag_size": "",
            "payload_length": "",
            "tag_endian": "",
            "header_hex": "",
            "error": str(exc),
        }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-root",
        required=True,
        help="Root folder containing stego PNG/BMP images."
    )

    parser.add_argument(
        "--out-csv",
        required=True,
        help="Output detailed CSV path."
    )

    parser.add_argument(
        "--summary-csv",
        required=True,
        help="Output summary CSV path."
    )

    args = parser.parse_args()

    input_root = Path(args.input_root).expanduser().resolve()
    out_csv = Path(args.out_csv).expanduser().resolve()
    summary_csv = Path(args.summary_csv).expanduser().resolve()

    image_paths = sorted(
        [
            p for p in input_root.rglob("*")
            if p.is_file() and p.suffix.lower() in [".png", ".bmp"]
        ]
    )

    if not image_paths:
        raise SystemExit(f"No PNG/BMP images found under: {input_root}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    start_time = time.time()
    total_images = len(image_paths)
    total_tests = total_images * 3
    completed_tests = 0

    print(f"Found {total_images} stego-images to validate.", flush=True)
    print(f"Total tests to run: {total_tests} because each image is tested at LSB 1, 2, and 3.", flush=True)
    print("-" * 90, flush=True)

    for idx, path in enumerate(image_paths, start=1):
        expected_type, expected_lsb = infer_expected_from_filename(path)

        elapsed = time.time() - start_time
        percent_images = (idx / total_images) * 100

        print(
            f"[IMAGE {idx}/{total_images}] {percent_images:.2f}% | "
            f"File: {path.name} | Expected: {expected_type} | Expected LSB: {expected_lsb} | "
            f"Elapsed: {elapsed:.1f}s",
            flush=True
        )

        for tested_lsb in (1, 2, 3):
            completed_tests += 1
            percent_tests = (completed_tests / total_tests) * 100

            print(
                f"    [TEST {completed_tests}/{total_tests}] {percent_tests:.2f}% | "
                f"Testing LSB {tested_lsb}...",
                flush=True
            )

            result = detect_one(path, tested_lsb)
            detected_type = result["detected_type"]

            is_expected_depth = tested_lsb == expected_lsb

            correct_at_expected_depth = (
                is_expected_depth and detected_type == expected_type
            )

            wrong_depth_should_be_unknown = (
                not is_expected_depth and detected_type == UNKNOWN
            )

            if is_expected_depth:
                check_status = (
                    "correct"
                    if correct_at_expected_depth
                    else "failed_expected_depth"
                )
            else:
                check_status = (
                    "correct_unknown_wrong_depth"
                    if wrong_depth_should_be_unknown
                    else "false_attribution_wrong_depth"
                )

            print(
                f"        Result: detected={detected_type} | "
                f"status={result['validation_status']} | check={check_status}",
                flush=True
            )

            rows.append({
                "image_path": str(path),
                "filename": path.name,
                "expected_type": expected_type,
                "expected_lsb": expected_lsb,
                "tested_lsb": tested_lsb,
                "detected_type": detected_type,
                "validation_status": result["validation_status"],
                "tag_size": result["tag_size"],
                "payload_length": result["payload_length"],
                "tag_endian": result["tag_endian"],
                "header_hex": result["header_hex"],
                "check_status": check_status,
                "error": result["error"],
            })

    fieldnames = list(rows[0].keys())

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    expected_depth_rows = [
        r for r in rows
        if int(r["tested_lsb"]) == int(r["expected_lsb"])
    ]

    wrong_depth_rows = [
        r for r in rows
        if int(r["tested_lsb"]) != int(r["expected_lsb"])
    ]

    expected_correct = sum(
        1 for r in expected_depth_rows
        if r["check_status"] == "correct"
    )

    expected_failed = len(expected_depth_rows) - expected_correct

    wrong_depth_unknown = sum(
        1 for r in wrong_depth_rows
        if r["check_status"] == "correct_unknown_wrong_depth"
    )

    wrong_depth_false = len(wrong_depth_rows) - wrong_depth_unknown

    processing_errors = sum(
        1 for r in rows
        if r["validation_status"] == "error"
    )

    elapsed_total = time.time() - start_time

    summary_rows = [
        {"metric": "images_tested", "value": len(image_paths)},
        {"metric": "total_lsb_tests", "value": len(rows)},
        {"metric": "expected_depth_tests", "value": len(expected_depth_rows)},
        {"metric": "expected_depth_correct", "value": expected_correct},
        {"metric": "expected_depth_failed", "value": expected_failed},
        {
            "metric": "expected_depth_accuracy_percent",
            "value": f"{(expected_correct / len(expected_depth_rows)) * 100:.2f}"
        },
        {"metric": "wrong_depth_tests", "value": len(wrong_depth_rows)},
        {"metric": "wrong_depth_unknown", "value": wrong_depth_unknown},
        {"metric": "wrong_depth_false_attributions", "value": wrong_depth_false},
        {"metric": "processing_errors", "value": processing_errors},
        {"metric": "elapsed_seconds", "value": f"{elapsed_total:.2f}"},
    ]

    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\n" + "=" * 90, flush=True)
    print("Saved detailed CSV:", out_csv, flush=True)
    print("Saved summary CSV:", summary_csv, flush=True)
    print("=" * 90, flush=True)

    print("\nSummary:", flush=True)
    for row in summary_rows:
        print(f"{row['metric']}: {row['value']}", flush=True)

    if expected_failed == 0 and wrong_depth_false == 0 and processing_errors == 0:
        print(
            "\nPASS: All expected-depth detections are correct, "
            "wrong-depth tests returned Unknown, and no processing errors occurred.",
            flush=True
        )
    else:
        print(
            "\nCHECK REQUIRED: Some failures, wrong-depth attributions, "
            "or processing errors were found.",
            flush=True
        )
        print(
            "Inspect rows where check_status is failed_expected_depth "
            "or false_attribution_wrong_depth.",
            flush=True
        )


if __name__ == "__main__":
    main()
