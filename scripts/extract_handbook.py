"""Extract text from ALL handbook PDFs into per-document text files.

Usage:  python scripts/extract_handbook.py            # processes every PDF in data/
        python scripts/extract_handbook.py <pdf>      # single file

(The extraction logic lives in agent/retriever.py so retrieval can also
auto-extract new documents lazily.)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agent.retriever import DATA, extract_pdf  # noqa: E402


def main():
    if len(sys.argv) > 1:
        print(extract_pdf(sys.argv[1]))
        return
    pdfs = [os.path.join(DATA, f) for f in sorted(os.listdir(DATA)) if f.lower().endswith(".pdf")]
    if not pdfs:
        print("No PDFs found in data/")
        return
    for p in pdfs:
        extract_pdf(p)
        print(f"extracted {os.path.basename(p)}")


if __name__ == "__main__":
    main()
