"""Extract text from the handbook PDF into data/handbook_text.txt.

Usage:  python scripts/extract_handbook.py [path_to_pdf]
Default expects data/student_handbook.pdf (already included).
"""
import os
import sys

from pypdf import PdfReader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "student_handbook.pdf")
    out = os.path.join(ROOT, "data", "handbook_text.txt")

    reader = PdfReader(pdf)
    parts, empty = [], 0
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            empty += 1
            text = f"[page {i + 1} - no extractable text]"
        parts.append(f"\n\n===== PAGE {i + 1} =====\n{text}")

    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(parts))

    print(f"pages={len(reader.pages)} empty={empty} -> {out}")


if __name__ == "__main__":
    main()
