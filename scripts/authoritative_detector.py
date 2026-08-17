"""
Authoritative StegoLSB-compatible payload reconstruction and file-type
attribution implementation used for all reported experiments.

Supported attribution targets:
    PDF, DOCX, XLSX, PPTX, RTF, EXE

Threat-model assumptions:
    - StegoLSB v1.7.1-compatible sequential embedding
    - PNG/BMP lossless carriers
    - 1, 2, or 3 LSBs
    - size tag generated on the study's little-endian x86-64 environment

The StegoLSB v1.7.1 size tag is serialized using sys.byteorder.
The study dataset was generated on a little-endian host; therefore the
authoritative experimental decoder explicitly uses little-endian order
to make reproduction independent of the evaluator's host architecture.
"""

from pathlib import Path
from PIL import Image
import io
import zipfile

from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


UNKNOWN = "Unknown/None"
STEGO_LSB_BYTE_ORDER = "little"


def flatten_image_data(img: Image.Image) -> tuple[list[int], int, int, int]:
    """Return image samples in StegoLSB raster/channel traversal order."""
    width, height = img.size
    num_channels = len(img.getbands())

    pixel_data = list(img.getdata())
    flat_data: list[int] = []

    if num_channels == 1:
        flat_data = [int(value) for value in pixel_data]
    else:
        for pixel in pixel_data:
            flat_data.extend(int(channel) for channel in pixel)

    return flat_data, num_channels, width, height


def matches_known_signature(data: bytes) -> bool:
    """Cheap primary-signature pre-check before full structural parsing."""
    return (
        data.startswith(b"PK\x03\x04")
        or data.startswith(b"%PDF")
        or data.startswith(b"{\\rtf1")
        or data.startswith(b"MZ")
    )


def identify_signature_only(data: bytes) -> tuple[str, str]:
    """
    Simple primary-signature baseline.

    OOXML files share the ZIP signature, so primary magic bytes alone
    cannot distinguish DOCX, XLSX, and PPTX; these are returned as ZIP.
    """
    if data.startswith(b"PK\x03\x04"):
        return "ZIP", "signature_pk_zip"

    if data.startswith(b"%PDF"):
        return "PDF", "signature_pdf"

    if data.startswith(b"{\\rtf1"):
        return "RTF", "signature_rtf"

    if data.startswith(b"MZ"):
        return "EXE", "signature_mz"

    return UNKNOWN, "no_known_signature"


def identify_structural(data: bytes) -> tuple[str, str]:
    """
    Structurally validate a reconstructed payload.

    Returns:
        (detected_type, validation_status)
    """

    if not data:
        return UNKNOWN, "empty_payload"

    # 1. Office Open XML: validate ZIP container and subtype structure.
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

    # 2. PDF: header plus terminal structural markers.
    if data.startswith(b"%PDF"):
        if b"startxref" in data and b"%%EOF" in data[-8192:]:
            return "PDF", "validated_pdf_startxref_eof"

        return UNKNOWN, "pdf_missing_startxref_or_eof"

    # 3. Windows PE executable: DOS header plus PE signature.
    if data.startswith(b"MZ"):
        if len(data) >= 0x40:
            pe_offset = int.from_bytes(
                data[0x3C:0x40],
                byteorder="little"
            )

            if 0 < pe_offset <= len(data) - 4:
                if data[pe_offset:pe_offset + 4] == b"PE\x00\x00":
                    return "EXE", "validated_mz_pe_header"

        return UNKNOWN, "mz_missing_valid_pe_header"

    # 4. RTF: primary signature plus basic internal/terminal structure.
    if data.startswith(b"{\\rtf1"):
        head = data[:512]

        if (
            b"\\ansi" in head
            or b"\\deff" in head
            or data.rstrip().endswith(b"}")
        ):
            return "RTF", "validated_rtf_structure"

        return UNKNOWN, "rtf_weak_structure"

    return UNKNOWN, "no_known_signature"


def detect_file_type(
    image_path: str | Path,
    lsb: int,
    mode: str = "structural",
) -> dict:
    """
    Reconstruct and attribute one StegoLSB-compatible payload.

    mode:
        "structural"     -> proposed structurally validated method
        "signature_only" -> simple signature baseline
    """

    image_path = Path(image_path)

    if lsb not in (1, 2, 3):
        raise ValueError("lsb must be one of: 1, 2, 3")

    if mode not in ("structural", "signature_only"):
        raise ValueError(
            "mode must be either 'structural' or 'signature_only'"
        )

    result = {
        "detected_type": UNKNOWN,
        "validation_status": "",
        "tag_size": "",
        "payload_length": "",
        "tag_endian": STEGO_LSB_BYTE_ORDER,
        "header_hex": "",
        "error": "",
    }

    try:
        with Image.open(image_path) as img:
            color_data, num_channels, width, height = flatten_image_data(img)

        # Maximum embeddable bitstream under the tested LSB depth.
        max_bits = num_channels * width * height * lsb

        # Same size-tag-width calculation used by StegoLSB v1.7.1.
        tag_size = roundup(max_bits.bit_length() / 8)

        result["tag_size"] = tag_size

        max_available_bits = len(color_data) * lsb
        max_available_bytes = max_available_bits // 8

        if max_available_bits < 8 * tag_size:
            result["validation_status"] = "incomplete_size_tag"
            return result

        # Reconstruct the StegoLSB size tag.
        tag_bytes = lsb_deinterleave_list(
            color_data,
            8 * tag_size,
            lsb,
        )

        if len(tag_bytes) < tag_size:
            result["validation_status"] = "incomplete_size_tag"
            result["header_hex"] = tag_bytes[:8].hex(" ")
            return result

        # Deterministic decoding matching the study's StegoLSB generation host.
        payload_length = int.from_bytes(
            tag_bytes[:tag_size],
            byteorder=STEGO_LSB_BYTE_ORDER,
        )

        result["payload_length"] = payload_length

        maximum_payload_bytes = max_available_bytes - tag_size

        if payload_length <= 0:
            result["validation_status"] = "invalid_payload_length"
            return result

        if payload_length > maximum_payload_bytes:
            result["validation_status"] = "payload_length_exceeds_capacity"
            return result

        # Cheap pre-check: reconstruct only the first 16 payload bytes.
        prefix_length = min(payload_length, 16)
        prefix_bytes_to_read = tag_size + prefix_length

        raw_prefix = lsb_deinterleave_list(
            color_data,
            8 * prefix_bytes_to_read,
            lsb,
        )

        candidate_prefix = raw_prefix[
            tag_size:tag_size + prefix_length
        ]

        result["header_hex"] = candidate_prefix[:8].hex(" ")

        if not matches_known_signature(candidate_prefix):
            result["validation_status"] = "no_known_signature"
            return result

        # Reconstruct exactly the payload length declared by the StegoLSB tag.
        full_bytes_to_read = tag_size + payload_length

        raw_extracted = lsb_deinterleave_list(
            color_data,
            8 * full_bytes_to_read,
            lsb,
        )

        candidate_payload = raw_extracted[
            tag_size:tag_size + payload_length
        ]

        if len(candidate_payload) != payload_length:
            result["validation_status"] = "incomplete_payload_reconstruction"
            return result

        if mode == "signature_only":
            detected_type, validation_status = identify_signature_only(
                candidate_payload
            )
        else:
            detected_type, validation_status = identify_structural(
                candidate_payload
            )

        result["detected_type"] = detected_type
        result["validation_status"] = validation_status
        result["header_hex"] = candidate_payload[:8].hex(" ")

        return result

    except Exception as exc:
        result["detected_type"] = "Processing Failed"
        result["validation_status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
