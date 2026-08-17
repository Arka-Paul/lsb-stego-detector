"""
Authoritative clean-image false-positive evaluation.

Evaluation set:
    16 original core clean carriers
    30 original XL clean carriers
    200 independent clean images
    ----------------------------
    246 unique clean images

Each image is examined at 1, 2, and 3 LSBs:
    246 x 3 = 738 clean-image tests.

The same authoritative reconstruction core used for the stego-image
experiment is used here.
"""

from pathlib import Path
import csv
import statistics
import time

from authoritative_detector import (
    detect_file_type,
    identify_signature_only,
    UNKNOWN,
)


DATASET_ROOT = Path("/home/kali/stego_dataset_expanded")

CORE_DIR = DATASET_ROOT / "covers_original"
XL_DIR = DATASET_ROOT / "covers_extended_xl"

EXPANDED_ROOT = (
    DATASET_ROOT / "clean_image_expanded_test"
)

EXPANDED_MANIFEST = (
    EXPANDED_ROOT
    / "manifests"
    / "expanded_clean_manifest.csv"
)

OUTPUT_CSV = Path(
    "results/authoritative_clean_738.csv"
)

SUMMARY_CSV = Path(
    "results/authoritative_clean_summary.csv"
)

COMBINED_MANIFEST = Path(
    "results/authoritative_clean_manifest_246.csv"
)


def image_files(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".png", ".bmp"}
    )


def baseline_from_header(header_hex: str) -> tuple[str, str]:
    if not header_hex:
        return UNKNOWN, "no_known_signature"

    try:
        data = bytes.fromhex(header_hex)
    except ValueError:
        return UNKNOWN, "invalid_header_hex"

    return identify_signature_only(data)


def build_clean_manifest() -> list[dict]:
    samples = []

    core_files = image_files(CORE_DIR)
    xl_files = image_files(XL_DIR)

    if len(core_files) != 16:
        raise RuntimeError(
            f"Expected 16 original core covers, found {len(core_files)}"
        )

    if len(xl_files) != 30:
        raise RuntimeError(
            f"Expected 30 original XL covers, found {len(xl_files)}"
        )

    for path in core_files:
        samples.append({
            "clean_id": f"original_core::{path.name}",
            "evaluation_group": "original",
            "subset": "core",
            "category": "controlled_original",
            "filename": path.name,
            "image_path": str(path.resolve()),
        })

    for path in xl_files:
        samples.append({
            "clean_id": f"original_xl::{path.name}",
            "evaluation_group": "original",
            "subset": "xl",
            "category": "controlled_original",
            "filename": path.name,
            "image_path": str(path.resolve()),
        })

    with EXPANDED_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        expanded_rows = list(csv.DictReader(f))

    if len(expanded_rows) != 200:
        raise RuntimeError(
            "Expected 200 expanded clean images, "
            f"found {len(expanded_rows)}"
        )

    for row in expanded_rows:
        path = EXPANDED_ROOT / row["relative_path"]

        if not path.is_file():
            raise FileNotFoundError(
                f"Expanded clean image not found: {path}"
            )

        samples.append({
            "clean_id": row["image_id"],
            "evaluation_group": "expanded",
            "subset": "independent",
            "category": row["category"],
            "filename": row["filename"],
            "image_path": str(path.resolve()),
        })

    if len(samples) != 246:
        raise RuntimeError(
            f"Expected 246 clean images, found {len(samples)}"
        )

    paths = [row["image_path"] for row in samples]

    if len(set(paths)) != 246:
        raise RuntimeError(
            "Clean-image manifest contains duplicate paths."
        )

    return samples


def summarise_group(rows: list[dict], name: str) -> dict:
    tests = len(rows)

    structural_fp = sum(
        int(r["structural_false_positive"])
        for r in rows
    )

    baseline_fp = sum(
        int(r["baseline_false_positive"])
        for r in rows
    )

    errors = sum(
        int(r["processing_error"])
        for r in rows
    )

    return {
        "group": name,
        "tests": tests,
        "structural_false_positives": structural_fp,
        "structural_fp_rate_percent":
            f"{100 * structural_fp / tests:.4f}"
            if tests else "0.0000",
        "baseline_false_positives": baseline_fp,
        "baseline_fp_rate_percent":
            f"{100 * baseline_fp / tests:.4f}"
            if tests else "0.0000",
        "processing_errors": errors,
    }


def main() -> None:
    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    samples = build_clean_manifest()

    # Preserve the exact 246-image clean evaluation set.
    with COMBINED_MANIFEST.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(samples[0].keys()),
        )
        writer.writeheader()
        writer.writerows(samples)

    print("Authoritative clean-image evaluation")
    print(f"Unique clean images : {len(samples)}")
    print(f"LSB depths          : 1, 2, 3")
    print(f"Total tests         : {len(samples) * 3}")
    print("-" * 72, flush=True)

    rows = []
    runtimes = []

    test_index = 0
    total_tests = len(samples) * 3

    start_all = time.perf_counter()

    for sample in samples:
        path = Path(sample["image_path"])

        for lsb in (1, 2, 3):
            test_index += 1

            start_one = time.perf_counter()

            result = detect_file_type(
                path,
                lsb,
                mode="structural",
            )

            runtime = time.perf_counter() - start_one
            runtimes.append(runtime)

            structural_detected = result["detected_type"]

            structural_fp = int(
                structural_detected
                not in (UNKNOWN, "Processing Failed")
            )

            baseline_detected, baseline_status = (
                baseline_from_header(
                    result["header_hex"]
                )
            )

            baseline_fp = int(
                baseline_detected != UNKNOWN
            )

            processing_error = int(
                result["validation_status"] == "error"
                or structural_detected == "Processing Failed"
            )

            rows.append({
                **sample,
                "tested_lsb": lsb,
                "baseline_detected_type":
                    baseline_detected,
                "baseline_status":
                    baseline_status,
                "baseline_false_positive":
                    baseline_fp,
                "structural_detected_type":
                    structural_detected,
                "structural_validation_status":
                    result["validation_status"],
                "structural_false_positive":
                    structural_fp,
                "tag_size":
                    result["tag_size"],
                "payload_length":
                    result["payload_length"],
                "tag_endian":
                    result["tag_endian"],
                "header_hex":
                    result["header_hex"],
                "runtime_seconds":
                    f"{runtime:.6f}",
                "processing_error":
                    processing_error,
                "error":
                    result["error"],
            })

            if (
                test_index == 1
                or test_index % 25 == 0
                or structural_fp
                or processing_error
                or test_index == total_tests
            ):
                elapsed = (
                    time.perf_counter() - start_all
                )

                print(
                    f"[{test_index:3d}/{total_tests}] "
                    f"{path.name} | "
                    f"lsb={lsb} | "
                    f"structural={structural_detected} | "
                    f"baseline={baseline_detected} | "
                    f"FP={structural_fp} | "
                    f"time={runtime:.3f}s | "
                    f"elapsed={elapsed:.1f}s",
                    flush=True,
                )

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = []

    summary_rows.append(
        summarise_group(rows, "combined_246")
    )

    original_rows = [
        r for r in rows
        if r["evaluation_group"] == "original"
    ]

    expanded_rows = [
        r for r in rows
        if r["evaluation_group"] == "expanded"
    ]

    summary_rows.append(
        summarise_group(
            original_rows,
            "original_46",
        )
    )

    summary_rows.append(
        summarise_group(
            expanded_rows,
            "expanded_200",
        )
    )

    for category in (
        "camera_photos",
        "screenshots",
        "document_scans",
        "noisy",
    ):
        category_rows = [
            r for r in expanded_rows
            if r["category"] == category
        ]

        summary_rows.append(
            summarise_group(
                category_rows,
                category,
            )
        )

    total_runtime = (
        time.perf_counter() - start_all
    )

    runtime_summary = {
        "group": "runtime",
        "tests": len(rows),
        "structural_false_positives": "",
        "structural_fp_rate_percent": "",
        "baseline_false_positives": "",
        "baseline_fp_rate_percent": "",
        "processing_errors": "",
        "total_runtime_seconds":
            f"{total_runtime:.6f}",
        "mean_runtime_seconds":
            f"{statistics.mean(runtimes):.6f}",
        "median_runtime_seconds":
            f"{statistics.median(runtimes):.6f}",
        "minimum_runtime_seconds":
            f"{min(runtimes):.6f}",
        "maximum_runtime_seconds":
            f"{max(runtimes):.6f}",
    }

    common_fields = [
        "group",
        "tests",
        "structural_false_positives",
        "structural_fp_rate_percent",
        "baseline_false_positives",
        "baseline_fp_rate_percent",
        "processing_errors",
        "total_runtime_seconds",
        "mean_runtime_seconds",
        "median_runtime_seconds",
        "minimum_runtime_seconds",
        "maximum_runtime_seconds",
    ]

    for row in summary_rows:
        for field in common_fields:
            row.setdefault(field, "")

    with SUMMARY_CSV.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=common_fields,
        )
        writer.writeheader()
        writer.writerows(summary_rows)
        writer.writerow(runtime_summary)

    print("\n" + "=" * 72)
    print("AUTHORITATIVE CLEAN SUMMARY")
    print("=" * 72)

    for row in summary_rows:
        print(
            f"{row['group']:20s} | "
            f"tests={row['tests']:3d} | "
            f"structural FP="
            f"{row['structural_false_positives']} | "
            f"baseline FP="
            f"{row['baseline_false_positives']} | "
            f"errors="
            f"{row['processing_errors']}"
        )

    print(f"\nDetailed CSV : {OUTPUT_CSV}")
    print(f"Summary CSV  : {SUMMARY_CSV}")
    print(f"Manifest CSV : {COMBINED_MANIFEST}")


if __name__ == "__main__":
    main()
