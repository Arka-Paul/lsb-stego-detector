from pathlib import Path
import csv
import subprocess
import sys

root = Path("/home/kali/Desktop/stego_dataset_expanded")
plan_file = root / "results" / "embedding_plan_combined.csv"
covers_original = root / "covers_original"
covers_xl = root / "covers_extended_xl"
payload_bank = root / "payload_bank"
output_dir = root / "stego_core_combined"
logs_dir = root / "logs"

output_dir.mkdir(parents=True, exist_ok=True)
logs_dir.mkdir(parents=True, exist_ok=True)

success_log = logs_dir / "embedding_success_combined.csv"
failure_log = logs_dir / "embedding_failure_combined.csv"


def find_payload(row: dict) -> Path:
    return payload_bank / row["payload_type"] / row["payload_size_class"] / row["payload_filename"]


def find_cover(row: dict) -> Path:
    if row["subset"] == "core":
        return covers_original / row["cover_filename"]
    elif row["subset"] == "extended_xl":
        return covers_xl / row["cover_filename"]
    raise ValueError(f"Unknown subset: {row['subset']}")


def build_output_path(row: dict) -> Path:
    ext = Path(row["cover_filename"]).suffix.lower()
    name = (
        f"{Path(row['cover_filename']).stem}__"
        f"{row['payload_type']}_{row['payload_size_class']}__"
        f"lsb{row['lsb']}{ext}"
    )
    return output_dir / name


def main() -> int:
    if not plan_file.exists():
        print(f"ERROR: embedding plan not found: {plan_file}", file=sys.stderr)
        return 1

    success_rows = []
    failure_rows = []

    total_attempted = 0
    total_success = 0
    total_failed = 0

    with plan_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["status"] != "OK":
                continue

            cover = find_cover(row)
            payload = find_payload(row)
            output = build_output_path(row)
            lsb = row["lsb"]

            if not cover.exists():
                failure_rows.append({
                    "subset": row["subset"],
                    "cover_filename": row["cover_filename"],
                    "payload_filename": row["payload_filename"],
                    "payload_type": row["payload_type"],
                    "payload_size_class": row["payload_size_class"],
                    "lsb": lsb,
                    "output_file": str(output),
                    "error": "Cover file not found"
                })
                total_failed += 1
                continue

            if not payload.exists():
                failure_rows.append({
                    "subset": row["subset"],
                    "cover_filename": row["cover_filename"],
                    "payload_filename": row["payload_filename"],
                    "payload_type": row["payload_type"],
                    "payload_size_class": row["payload_size_class"],
                    "lsb": lsb,
                    "output_file": str(output),
                    "error": "Payload file not found"
                })
                total_failed += 1
                continue

            if output.exists():
                output.unlink()

            total_attempted += 1

            cmd = [
                "stegolsb",
                "steglsb",
                "-h",
                "-i", str(cover),
                "-s", str(payload),
                "-o", str(output),
                "-n", str(lsb),
            ]

            try:
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )

                success_rows.append({
                    "subset": row["subset"],
                    "cover_filename": row["cover_filename"],
                    "payload_filename": row["payload_filename"],
                    "payload_type": row["payload_type"],
                    "payload_size_class": row["payload_size_class"],
                    "lsb": lsb,
                    "output_file": str(output),
                    "stdout": result.stdout.strip(),
                })
                total_success += 1

            except subprocess.CalledProcessError as exc:
                total_failed += 1
                failure_rows.append({
                    "subset": row["subset"],
                    "cover_filename": row["cover_filename"],
                    "payload_filename": row["payload_filename"],
                    "payload_type": row["payload_type"],
                    "payload_size_class": row["payload_size_class"],
                    "lsb": lsb,
                    "output_file": str(output),
                    "error": exc.stderr.strip() if exc.stderr else str(exc),
                    "stdout": exc.stdout.strip() if exc.stdout else "",
                })

            except Exception as exc:
                total_failed += 1
                failure_rows.append({
                    "subset": row["subset"],
                    "cover_filename": row["cover_filename"],
                    "payload_filename": row["payload_filename"],
                    "payload_type": row["payload_type"],
                    "payload_size_class": row["payload_size_class"],
                    "lsb": lsb,
                    "output_file": str(output),
                    "error": str(exc),
                })

    if success_rows:
        with success_log.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["subset", "cover_filename", "payload_filename", "payload_type",
                            "payload_size_class", "lsb", "output_file", "stdout"]
            )
            writer.writeheader()
            writer.writerows(success_rows)

    if failure_rows:
        with failure_log.open("w", newline="", encoding="utf-8") as f:
            fieldnames = set()
            for row in failure_rows:
                fieldnames.update(row.keys())
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(failure_rows)

    print("\n==================== SUMMARY ====================")
    print(f"Total attempted : {total_attempted}")
    print(f"Total success   : {total_success}")
    print(f"Total failed    : {total_failed}")
    print(f"Success log     : {success_log}")
    print(f"Failure log     : {failure_log}")
    print("================================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
