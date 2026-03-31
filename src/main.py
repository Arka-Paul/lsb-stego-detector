import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image
from stego_lsb.bit_manipulation import lsb_deinterleave_list, roundup


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
        self.root.geometry("900x600")

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
            length=850,
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

        self.tree.column("File", width=250)
        self.tree.column("LSB", width=60, anchor="center")
        self.tree.column("Detected Type", width=220)
        self.tree.column("Hex Header", width=220)

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

    def identify_format(self, data: bytes) -> str:
        for signature, format_name in MAGIC_BYTES.items():
            if data.startswith(signature):
                if signature == b"PK\x03\x04":
                    if b"word/" in data:
                        return "DOCX (Word Document)"
                    if b"xl/" in data:
                        return "XLSX (Excel Spreadsheet)"
                    if b"ppt/" in data:
                        return "PPTX (PowerPoint Presentation)"
                    return "Office Document or ZIP Archive"
                return format_name
        return "Unknown/None"

    def _flatten_image_data(self, img: Image.Image) -> tuple[list[int], int, int, int]:
        """
        Converts image pixel data into a flat integer list and returns:
        (flat_pixel_values, num_channels, width, height)

        This handles both grayscale and multi-channel images safely.
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
                img = Image.open(path)
                color_data, num_channels, width, height = self._flatten_image_data(img)

                for lsb in lsb_list:
                    max_bits = num_channels * width * height * lsb
                    tag_size = roundup(max_bits.bit_length() / 8)

                    # Reads beyond the tag area so that deeper markers
                    # such as Office ZIP structure can still be found.
                    bytes_to_read = tag_size + 10000
                    bits_to_read = 8 * bytes_to_read

                    # Prevent overshooting available carrier data
                    max_available_bits = len(color_data) * lsb
                    if bits_to_read > max_available_bits:
                        bits_to_read = max_available_bits

                    if bits_to_read <= 0:
                        self.tree.insert(
                            "",
                            "end",
                            values=(filename, lsb, "Unknown/None", "No data")
                        )
                        continue

                    raw_extracted = lsb_deinterleave_list(
                        color_data,
                        bits_to_read,
                        lsb
                    )

                    file_header = raw_extracted[tag_size:] if len(raw_extracted) > tag_size else b""
                    detected_format = self.identify_format(file_header)
                    hex_header = file_header[:8].hex(" ") if file_header else "No data"

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

def main():
    root = tk.Tk()
    app = LSBStegoDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()