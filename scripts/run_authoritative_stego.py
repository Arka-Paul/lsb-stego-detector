"""
Authoritative manifest-driven evaluation of the 1,848 stego-images.

Each manifest row is evaluated exactly once at its known embedding depth.
The proposed structural method and a simple primary-signature baseline
are reported from the same reconstructed sample.

The manifest determines the evaluation set; directory recursion is not used.
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


MANIFEST = Path(
    "/home/kali/stego_dataset_expanded/results/stego_manifest_combined.csv"
)

DATASET_ROOT = Path("/home/kali/stego_dataset_expanded")

OUTPUT_CSV = Path(
    "results/authoritative_stego_1848.csv"
)

SUMMARY_CSV = Path(
    "results/authoritative_stego_summary.csv"
)


def resolve_stego_path(stored_path: str) -> Path:
    """
    Resolve historical absolute manifest paths against the current
    dataset root without modifying the preserved original manifest.
    """
    marker = "stego_dataset_expanded/"

    if marker not in stored_path:
        raise ValueError(
            f"Cannot derive dataset-relative path from: {stored_path}"
        )

    relative = stored_path.split(marker, 1)[1]
    return DATASET_ROOT / relative


def baseline_from_header(header_hex: str) -> tuple[str, str]:
    """
    Primary-magic-byte baseline using the same reconstructed header
    produced by the authoritative detector.

    OOXML files share the PK ZIP signature; therefore this deliberately
    reports ZIP rather than guessing DOCX/XLSX/PPTX.
    """
    if not header_hex:
        return UNKNOWN, "no_known_signature"

    try:
        data = bytes.fromhex(header_hex)
    except ValueError:
        return UNKNOWN, "invalid_header_hex"

    return identify_signature_only(data)


def main() -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with MANIFEST.open(newline="", encoding="utf-8") as f:
        manifest_rows = list(csv.DictReader(f))

    if len(manifest_rows) != 1848:
        raise SystemExit(
            f"Expected 1848 manifest rows, found {len(manifest_rows)}"
        )

    print("Authoritative stego evaluation")
    print(f"Manifest : {MANIFEST}")
    print(f"Samples  : {len(manifest_rows)}")
    print("-" * 72, flush=True)

    rows = []
    runtimes = []

    structural_correct = 0
    baseline_exact_correct = 0
    processing_errors = 0

    start_all = time.perf_counter()

    for index, row in enumerate(manifest_rows, start=1):
        path = resolve_stego_path(row["stego_path"])

        if not path.is_file():
            raise FileNotFoundError(
                f"Manifest sample does not exist: {path}"
            )

        lsb = int(row["lsb"])
        expected = row["expected_type"].strip().upper()

        start_one = time.perf_counter()

        result = detect_file_type(
            path,
            lsb,
            mode="structural",
        )

        runtime = time.perf_counter() - start_one
        runtimes.append(runtime)

        structural_detected = result["detected_type"]
        structural_is_correct = int(
            structural_detected.upper() == expected
        )

        structural_correct += structural_is_correct

        if result["validation_status"] == "error":
            processing_errors += 1

        baseline_detected, baseline_status = baseline_from_header(
            result["header_hex"]
        )

        baseline_is_correct = int(
            baseline_detected.upper() == expected
        )

        baseline_exact_correct += baseline_is_correct

        rows.append({
            **row,
            "resolved_stego_path": str(path),
            "baseline_detected_type": baseline_detected,
            "baseline_status": baseline_status,
            "baseline_exact_correct": baseline_is_correct,
            "structural_detected_type": structural_detected,
            "structural_validation_status": result["validation_status"],
            "structural_correct": structural_is_correct,
            "tag_size": result["tag_size"],
            "payload_length": result["payload_length"],
            "tag_endian": result["tag_endian"],
            "header_hex": result["header_hex"],
            "runtime_seconds": f"{runtime:.6f}",
            "error": result["error"],
        })

        if (
            index == 1
            or index % 25 == 0
            or structural_is_correct == 0
            or result["validation_status"] == "error"
            or index == len(manifest_rows)
        ):
            elapsed = time.perf_counter() - start_all

            print(
                f"[{index:4d}/{len(manifest_rows)}] "
                f"{path.name} | "
                f"expected={expected} | "
                f"structural={structural_detected} | "
                f"baseline={baseline_detected} | "
                f"length={result['payload_length']} | "
                f"time={runtime:.3f}s | "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )

    total_runtime = time.perf_counter() - start_all

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    mean_runtime = statistics.mean(runtimes)
    median_runtime = statistics.median(runtimes)
    minimum_runtime = min(runtimes)
    maximum_runtime = max(runtimes)

    summary = [
        ("manifest_rows", len(manifest_rows)),
        ("samples_tested", len(rows)),
        ("structural_correct", structural_correct),
        (
            "structural_incorrect",
            len(rows) - structural_correct
        ),
        (
            "structural_accuracy_percent",
            f"{100 * structural_correct / len(rows):.4f}"
        ),
        ("processing_errors", processing_errors),
        ("baseline_exact_correct", baseline_exact_correct),
        (
            "baseline_exact_incorrect",
            len(rows) - baseline_exact_correct
        ),
        (
            "baseline_exact_accuracy_percent",
            f"{100 * baseline_exact_correct / len(rows):.4f}"
        ),
        ("total_runtime_seconds", f"{total_runtime:.6f}"),
        ("mean_runtime_seconds", f"{mean_runtime:.6f}"),
        ("median_runtime_seconds", f"{median_runtime:.6f}"),
        ("minimum_runtime_seconds", f"{minimum_runtime:.6f}"),
        ("maximum_runtime_seconds", f"{maximum_runtime:.6f}"),
    ]

    with SUMMARY_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerows(summary)

    print("\n" + "=" * 72)
    print("AUTHORITATIVE STEGO SUMMARY")
    print("=" * 72)

    for metric, value in summary:
        print(f"{metric:38s}: {value}")

    print(f"\nDetailed CSV : {OUTPUT_CSV}")
    print(f"Summary CSV  : {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
