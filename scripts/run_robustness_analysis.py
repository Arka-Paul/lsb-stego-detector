import csv
from pathlib import Path
from collections import defaultdict

import cv2
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path("/home/kali/Desktop/stego_dataset_expanded")
MANIFEST = ROOT / "results" / "stego_manifest_combined.csv"
ROBUST_DIR = ROOT / "robustness_test"
RESULTS_DIR = ROOT / "results"

ROBUST_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PER_FILE = RESULTS_DIR / "robustness_results_per_file.csv"
OUTPUT_SUMMARY = RESULTS_DIR / "robustness_table.csv"
OUTPUT_SELECTED = RESULTS_DIR / "robustness_selected_subset.csv"

import sys
sys.path.insert(0, str(ROOT / "scripts"))
from detector_cli import detect_file_type as detect_full
from detector_ablation import detect_file_type as detect_ablation


def choose_wrong_lsb(true_lsb: int) -> int:
    if true_lsb == 1:
        return 2
    if true_lsb == 2:
        return 1
    if true_lsb == 3:
        return 2
    raise ValueError(f"Unexpected LSB value: {true_lsb}")


def add_gaussian_noise_safe(image_bgr: np.ndarray, sigma: float = 8.0) -> np.ndarray:
    if image_bgr is None:
        raise ValueError("OpenCV failed to load image")

    noise = np.random.normal(0, sigma, image_bgr.shape).astype(np.float32)
    noisy = image_bgr.astype(np.float32) + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    return noisy


def classify_outcome(predicted: str, expected: str) -> str:
    p = predicted.strip().upper()
    e = expected.strip().upper()

    if p == e:
        return "Correct"
    if p in {"UNKNOWN", "UNKNOWN/NONE", "NONE", "ZIP"}:
        return "Unknown"
    if p == "ERROR":
        return "Error"
    return "Misclassified"


def build_subset(manifest_path: Path) -> list[dict]:
    """
    Select exactly 36 images:
    6 payload types × 2 subsets × 3 LSB depths

    Selection rule:
    For each (subset, payload_type, lsb), choose the first filename
    in alphabetical order from the real manifest.
    """
    rows = []
    with manifest_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    payload_order = ["DOCX", "EXE", "PDF", "PPTX", "RTF", "XLSX"]
    subset_order = ["core", "extended_xl"]
    lsb_order = [1, 2, 3]

    grouped = defaultdict(list)
    for row in rows:
        key = (
            row["subset"],
            row["payload_type"].strip().upper(),
            int(row["lsb"])
        )
        grouped[key].append(row)

    selected = []

    for subset in subset_order:
        for payload in payload_order:
            for lsb in lsb_order:
                key = (subset, payload, lsb)
                candidates = grouped.get(key, [])

                if not candidates:
                    raise ValueError(
                        f"No candidate found for subset={subset}, payload={payload}, lsb={lsb}"
                    )

                chosen = sorted(candidates, key=lambda r: r["stego_filename"])[0]
                selected.append(chosen)

    return selected


def save_as_jpeg(src: Path, dst: Path, quality: int = 85):
    img = Image.open(src).convert("RGB")
    img.save(dst, "JPEG", quality=quality)


def save_resized_png(src: Path, dst: Path, scale: float = 0.9):
    img = Image.open(src).convert("RGB")
    new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
    img = img.resize(new_size)
    img.save(dst, "PNG")


def save_noisy_png(src: Path, dst: Path, sigma: float = 8.0):
    img_bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    noisy = add_gaussian_noise_safe(img_bgr, sigma=sigma)
    cv2.imwrite(str(dst), noisy)


def evaluate_scenario(path: Path, true_lsb: int, expected: str, scenario: str):
    try:
        if scenario == "Original":
            predicted = detect_full(str(path), true_lsb).strip().upper()

        elif scenario == "JPEG Compression":
            predicted = detect_full(str(path), true_lsb).strip().upper()

        elif scenario == "Resizing":
            predicted = detect_full(str(path), true_lsb).strip().upper()

        elif scenario == "Slight Noise":
            predicted = detect_full(str(path), true_lsb).strip().upper()

        elif scenario == "Wrong LSB Depth":
            wrong_lsb = choose_wrong_lsb(true_lsb)
            predicted = detect_full(str(path), wrong_lsb).strip().upper()

        elif scenario == "Reduced Buffer":
            predicted = detect_ablation(str(path), true_lsb, "no_buffer").strip().upper()

        else:
            predicted = "ERROR"

        if predicted == "":
            predicted = "UNKNOWN"

    except Exception:
        predicted = "ERROR"

    outcome = classify_outcome(predicted, expected)
    return predicted, outcome


def run_robustness():
    subset = build_subset(MANIFEST)

    # Save and print the exact 36 selected images
    selected_rows = []
    print("\n==================== SELECTED ROBUSTNESS SUBSET ====================")
    for i, row in enumerate(subset, start=1):
        selected_rows.append({
            "index": i,
            "subset": row["subset"],
            "payload_type": row["payload_type"].upper(),
            "payload_size_class": row["payload_size_class"],
            "lsb": row["lsb"],
            "stego_filename": row["stego_filename"],
            "cover_filename": row["cover_filename"],
        })
        print(
            f"[{i:02d}] subset={row['subset']:<11} "
            f"payload={row['payload_type'].upper():<4} "
            f"lsb={row['lsb']} "
            f"file={row['stego_filename']}"
        )

    pd.DataFrame(selected_rows).to_csv(OUTPUT_SELECTED, index=False)
    print(f"\nSaved selected subset list: {OUTPUT_SELECTED}")

    results = []

    for idx, row in enumerate(subset, start=1):
        src = Path(row["stego_path"])
        expected = row["expected_type"].upper()
        true_lsb = int(row["lsb"])
        subset_name = row["subset"]
        filename = row["stego_filename"]

        print(f"\n[{idx}/{len(subset)}] Testing {filename}")

        stem = src.stem
        jpeg_path = ROBUST_DIR / f"{stem}__jpeg_q85.jpg"
        resize_path = ROBUST_DIR / f"{stem}__resize_90.png"
        noise_path = ROBUST_DIR / f"{stem}__noise.png"

        save_as_jpeg(src, jpeg_path, quality=85)
        save_resized_png(src, resize_path, scale=0.9)
        save_noisy_png(src, noise_path, sigma=8.0)

        scenarios = {
            "Original": src,
            "JPEG Compression": jpeg_path,
            "Resizing": resize_path,
            "Slight Noise": noise_path,
            "Wrong LSB Depth": src,
            "Reduced Buffer": src,
        }

        for scenario_name, path in scenarios.items():
            predicted, outcome = evaluate_scenario(
                path=path,
                true_lsb=true_lsb,
                expected=expected,
                scenario=scenario_name
            )

            results.append({
                "scenario": scenario_name,
                "file": filename,
                "subset": subset_name,
                "expected_type": expected,
                "true_lsb": true_lsb,
                "tested_path": str(path),
                "predicted_type": predicted,
                "outcome": outcome,
                "correct": 1 if outcome == "Correct" else 0,
                "unknown": 1 if outcome == "Unknown" else 0,
                "misclassified": 1 if outcome == "Misclassified" else 0,
                "error": 1 if outcome == "Error" else 0,
            })

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_PER_FILE, index=False)

    summary = (
        df.groupby("scenario")
        .agg(
            Samples=("file", "count"),
            Correct=("correct", "sum"),
            Unknown=("unknown", "sum"),
            Misclassified=("misclassified", "sum"),
            Error=("error", "sum"),
        )
        .reset_index()
    )

    summary["Accuracy"] = (summary["Correct"] / summary["Samples"] * 100).map(lambda x: f"{x:.2f}%")
    summary.to_csv(OUTPUT_SUMMARY, index=False)

    print("\n==================== ROBUSTNESS SUMMARY ====================")
    print(summary.to_string(index=False))
    print(f"\nSaved per-file results : {OUTPUT_PER_FILE}")
    print(f"Saved summary table    : {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    run_robustness()
