import os
import re

import chromadb

from ..config import settings
from ..llm import _client

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
COLLECTION_NAME = "leaseguardian_clauses"


def _embed(text: str) -> list[float]:
    resp = _client.embeddings.create(model=settings.openai_embed_model, input=text)
    return resp.data[0].embedding


def load_checkout_clauses(path: str = os.path.join(DOCS_DIR, "checkout.md")):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    chunks = []
    for part in re.split(r"\n(?=## )", content):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"##\s+(\S+)\s+(.+)", part.splitlines()[0])
        if not m:
            continue
        chunks.append({
            "id": f"checkout-{m.group(1)}",
            "clause_no": m.group(1),
            "title": m.group(2).strip(),
            "text": part,
        })
    return chunks


def ingest():
    client = chromadb.PersistentClient(path=os.path.join(os.path.dirname(__file__), "chroma_db"))
    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    chunks = load_checkout_clauses()
    col.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{
            "domain": "checkout",
            "doc_id": "checkout_policy",
            "clause_no": c["clause_no"],
            "title": c["title"],
        } for c in chunks],
        embeddings=[_embed(c["text"]) for c in chunks],
    )
    print(f"ingested {len(chunks)} checkout clauses")


if __name__ == "__main__":
    ingest()