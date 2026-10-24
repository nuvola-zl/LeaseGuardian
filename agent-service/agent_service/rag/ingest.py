from __future__ import annotations

import argparse
from pathlib import Path

from .core import parse_markdown_to_docs, replace_domain_documents

ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = ROOT / "rag" / "docs"


def ingest_domain(domain: str) -> int:
    if domain == "repair":
        files = [DOCS_DIR / "repair_policy.md", DOCS_DIR / "price_table.md"]
    elif domain == "checkout":
        files = [DOCS_DIR / "checkout.md"]
    else:
        raise ValueError(f"unknown domain: {domain}")

    docs = []
    for path in files:
        if not path.exists():
            raise FileNotFoundError(f"missing file: {path}")
        docs.extend(
            parse_markdown_to_docs(
                markdown=path.read_text(encoding="utf-8"),
                domain=domain,
                doc_id=path.stem,
            )
        )

    replace_domain_documents(domain, docs)
    print(f"[ingest] domain={domain} docs={len(docs)}")
    return len(docs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("domain", choices=["repair", "checkout", "all"])
    args = parser.parse_args()

    if args.domain in ("repair", "all"):
        ingest_domain("repair")
    if args.domain in ("checkout", "all"):
        ingest_domain("checkout")


if __name__ == "__main__":
    main()