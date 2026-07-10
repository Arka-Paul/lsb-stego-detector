import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image
import io
import zipfile
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


UNKNOWN = "Unknown/None"

MAGIC_BYTES = {
    b"PK\x03\x04": "Office Document (DOCX/XLSX/PPTX)",
    b"%PDF": "PDF Document",
    b"{\\rtf1": "Rich Text Format (RTF)",
    b"MZ": "Windows Executable (EXE)",
}


class LSBStegoDetectorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Batch LSB Stego Detector")
        self.root.geometry("950x620")

        self.file_paths: list[Path] = []

        self._build_header()
        self._build_progress_bar()
        self._build_table()

    def _build_header(self) -> None:
        header_frame = tk.Frame(self.root)
        header_frame.pack(pady=10, fill="x", padx=20)

        tk.Button(
            header_frame,
            text="1. Select Images",
            command=self.load_images,
            width=15
        ).pack(side="left")

        self.lbl_count = tk.Label(header_frame, text="0 files selected", fg="blue")
        self.lbl_count.pack(side="left", padx=10)

        tk.Label(
            header_frame,
            text="2. Enter LSBs (e.g. 1, 2, 3):"
        ).pack(side="left", padx=(20, 5))

        self.lsb_input = tk.Entry(header_frame, width=10)
        self.lsb_input.insert(0, "1, 2, 3")
        self.lsb_input.pack(side="left")

        tk.Button(
            header_frame,
            text="3. Run Analysis",
            command=self.analyze_batch,
            bg="#2c3e50",
            fg="white",
            width=15
        ).pack(side="right")

    def _build_progress_bar(self) -> None:
        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=900,
            mode="determinate"
        )
        self.progress.pack(pady=5)

    def _build_table(self) -> None:
        table_frame = tk.Frame(self.root)
        table_frame.pack(expand=True, fill="both", padx=10, pady=10)

        columns = ("File", "LSB", "Detected Type", "Hex Header")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("File", width=280)
        self.tree.column("LSB", width=60, anchor="center")
        self.tree.column("Detected Type", width=260)
        self.tree.column("Hex Header", width=260)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar.pack(side="right", fill="y")

    def load_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select PNG or BMP images",
            filetypes=[("Lossless Images", "*.png *.bmp")]
        )

        if files:
            self.file_paths = [Path(file) for file in files]
            self.lbl_count.config(text=f"{len(self.file_paths)} files selected")

    def _matches_known_signature(self, data: bytes) -> bool:
        return any(data.startswith(signature) for signature in MAGIC_BYTES)

    def identify_format(self, data: bytes) -> str:
        """
        Performs structural validation beyond short magic-byte matching.
        Returns a specific detected type or Unknown/None.
        """

        if not data:
            return UNKNOWN

        # 1. Office Open XML / ZIP-family validation
        if data.startswith(b"PK\x03\x04"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    # Opening ZipFile requires a valid ZIP central directory.
                    # testzip() performs CRC/integrity checking.
                    if zf.testzip() is not None:
                        return UNKNOWN

                    namelist = zf.namelist()

                    # Office Open XML files should contain [Content_Types].xml.
                    if "[Content_Types].xml" not in namelist:
                        return UNKNOWN

                    # Subtype-specific Office markers.
                    if any(name.startswith("word/") for name in namelist):
                        return "DOCX (Word Document)"

                    if any(name.startswith("xl/") for name in namelist):
                        return "XLSX (Excel Spreadsheet)"

                    if any(name.startswith("ppt/") for name in namelist):
                        return "PPTX (PowerPoint Presentation)"

                    return "Office Document or ZIP Archive"

            except (
                zipfile.BadZipFile,
                zipfile.LargeZipFile,
                RuntimeError,
                ValueError,
                NotImplementedError,
                OSError,
            ):
                return UNKNOWN

        # 2. PDF validation: header + trailer-related markers
        if data.startswith(b"%PDF"):
            # A valid PDF normally contains startxref and %%EOF near the end.
            if b"startxref" in data and b"%%EOF" in data[-8192:]:
                return "PDF Document"
            return UNKNOWN

        # 3. Windows PE executable validation
        if data.startswith(b"MZ"):
            if len(data) >= 0x40:
                pe_offset = int.from_bytes(data[0x3C:0x40], byteorder="little")
                if 0 < pe_offset < len(data) - 4:
                    if data[pe_offset:pe_offset + 4] == b"PE\x00\x00":
                        return "Windows Executable (EXE)"
            return UNKNOWN

        # 4. RTF validation: plaintext markup with basic structural checks
        if data.startswith(b"{\\rtf1"):
            head = data[:512]
            if b"\\ansi" in head or b"\\deff" in head or data.rstrip().endswith(b"}"):
                return "Rich Text Format (RTF)"
            return UNKNOWN

        return UNKNOWN

    def _flatten_image_data(self, img: Image.Image) -> tuple[list[int], int, int, int]:
        """
        Converts image pixel data into a flat integer list and returns:
        (flat_pixel_values, num_channels, width, height)

        This handles both grayscale and multi-channel images.
        """
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

    def _decode_candidate_lengths(
        self,
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

        # Remove duplicates while preserving order.
        unique_candidates: list[tuple[str, int]] = []
        seen_lengths: set[int] = set()

        for endian, length in candidate_lengths:
            if length not in seen_lengths:
                unique_candidates.append((endian, length))
                seen_lengths.add(length)

        return unique_candidates

    def analyze_batch(self) -> None:
        if not self.file_paths:
            messagebox.showerror("Error", "Please select images first.")
            return

        try:
            lsb_list = [int(x.strip()) for x in self.lsb_input.get().split(",")]
        except ValueError:
            messagebox.showerror("Error", "Invalid LSB input. Use numbers like: 1, 2, 3")
            return

        if any(lsb <= 0 for lsb in lsb_list):
            messagebox.showerror("Error", "LSB values must be positive integers.")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.progress["maximum"] = len(self.file_paths)
        self.progress["value"] = 0

        for idx, path in enumerate(self.file_paths):
            filename = path.name

            try:
                with Image.open(path) as img:
                    color_data, num_channels, width, height = self._flatten_image_data(img)

                for lsb in lsb_list:
                    max_bits = num_channels * width * height * lsb
                    tag_size = roundup(max_bits.bit_length() / 8)

                    max_available_bits = len(color_data) * lsb
                    max_available_bytes = max_available_bits // 8

                    # Step 1: read only the stego-lsb size tag.
                    tag_bits_to_read = min(8 * tag_size, max_available_bits)

                    if tag_bits_to_read <= 0:
                        self.tree.insert(
                            "",
                            "end",
                            values=(filename, lsb, UNKNOWN, "No data")
                        )
                        continue

                    tag_bytes = lsb_deinterleave_list(
                        color_data,
                        tag_bits_to_read,
                        lsb
                    )

                    if len(tag_bytes) < tag_size:
                        self.tree.insert(
                            "",
                            "end",
                            values=(filename, lsb, UNKNOWN, "Incomplete tag")
                        )
                        continue

                    candidate_lengths = self._decode_candidate_lengths(
                        tag_bytes=tag_bytes,
                        tag_size=tag_size,
                        max_available_bytes=max_available_bytes
                    )

                    if not candidate_lengths:
                        self.tree.insert(
                            "",
                            "end",
                            values=(filename, lsb, UNKNOWN, tag_bytes[:8].hex(" "))
                        )
                        continue

                    detected_format = UNKNOWN
                    display_header = b""

                    # Step 2: test plausible payload-length interpretations.
                    for endian, payload_length in candidate_lengths:
                        # Read only a short prefix first. If no known signature appears,
                        # avoid extracting a full random clean-image payload.
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

                        if not display_header:
                            display_header = candidate_prefix

                        if not self._matches_known_signature(candidate_prefix):
                            continue

                        # Step 3: extract the full payload candidate for structural validation.
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

                        trial_format = self.identify_format(candidate_payload)

                        if trial_format != UNKNOWN:
                            detected_format = trial_format
                            display_header = candidate_payload[:16]
                            break

                    hex_header = display_header[:8].hex(" ") if display_header else "No data"

                    self.tree.insert(
                        "",
                        "end",
                        values=(filename, lsb, detected_format, hex_header)
                    )

            except Exception as exc:
                self.tree.insert(
                    "",
                    "end",
                    values=(filename, "Error", "Processing Failed", str(exc))
                )

            self.progress["value"] = idx + 1
            self.root.update_idletasks()

        messagebox.showinfo("Done", f"Processed {len(self.file_paths)} images.")


def main() -> None:
    root = tk.Tk()
    LSBStegoDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
