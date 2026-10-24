from __future__ import annotations

import os
import re
from typing import Any, Optional

import chromadb
from rank_bm25 import BM25Okapi

from ..config import settings
from ..llm import get_openai_client

COLLECTION_NAME = "leaseguardian_clauses"
_CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")

_chroma_client = None
_BM25_CACHE: dict[str, tuple[Optional[BM25Okapi], list[dict[str, Any]]]] = {}


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=_CHROMA_DIR)
    return _chroma_client


def _get_collection():
    return _get_chroma_client().get_or_create_collection(name=COLLECTION_NAME)


def _embed(text: str) -> list[float]:
    if not getattr(settings, "openai_embed_model", None):
        raise RuntimeError("OPENAI_EMBED_MODEL is not configured")
    resp = get_openai_client().embeddings.create(
        model=settings.openai_embed_model,
        input=text,
    )
    return resp.data[0].embedding


def _load_domain_docs(domain: str) -> list[dict[str, Any]]:
    if domain in _BM25_CACHE:
        return _BM25_CACHE[domain][1]

    col = _get_collection()
    try:
        result = col.get(where={"domain": domain}, include=["documents", "metadatas"])
    except Exception:
        docs: list[dict[str, Any]] = []
        _BM25_CACHE[domain] = (None, docs)
        return docs

    docs = []
    for doc, meta, doc_id in zip(result.get("documents", []), result.get("metadatas", []), result.get("ids", [])):
        docs.append({
            "id": doc_id,
            "text": doc,
            "domain": meta.get("domain"),
            "doc_id": meta.get("doc_id"),
            "clause_no": meta.get("clause_no"),
            "title": meta.get("title"),
        })

    index = None
    if docs:
        tokenized = [list(d["text"]) for d in docs]  # 中文按字切，规避分词依赖
        index = BM25Okapi(tokenized)

    _BM25_CACHE[domain] = (index, docs)
    return docs


def _bm25_top(query: str, domain: str, top_k: int) -> list[dict[str, Any]]:
    if domain not in _BM25_CACHE:
        _load_domain_docs(domain)
    index, docs = _BM25_CACHE[domain]
    if index is None or not docs:
        return []

    scores = index.get_scores(list(query))
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [
        {**d, "score": float(s), "source": "bm25"}
        for d, s in ranked if s > 0
    ]


def _vector_top(query: str, domain: str, top_k: int) -> list[dict[str, Any]]:
    col = _get_collection()
    result = col.query(
        query_embeddings=[_embed(query)],
        n_results=top_k,
        where={"domain": domain},
    )

    items = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    for doc_id, doc, meta, dist in zip(ids, docs, metas, dists):
        items.append({
            "id": doc_id,
            "text": doc,
            "domain": meta.get("domain"),
            "doc_id": meta.get("doc_id"),
            "clause_no": meta.get("clause_no"),
            "title": meta.get("title"),
            "score": 1 - dist,
            "source": "vector",
        })
    return items


def _rrf_fuse(lists: list[list[dict[str, Any]]], k: int = 60) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for lst in lists:
        for rank, item in enumerate(lst):
            key = item["id"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            by_id[key] = item
    ranked = sorted(by_id.values(), key=lambda x: scores[x["id"]], reverse=True)
    for item in ranked:
        item["rrf_score"] = scores[item["id"]]
    return ranked


def _rerank(query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    预留 rerank。
    当前恒等；以后接 bge-reranker 只改这里。
    """
    return candidates


def retrieve_clauses(query: str, domain: str, top_k: int = 2,
                     score_threshold: Optional[float] = None) -> list[dict[str, Any]]:
    """
    统一检索入口：所有业务域共用。
    domain 例：repair / checkout
    """
    bm25_hits = _bm25_top(query, domain=domain, top_k=top_k * 2)
    vec_hits = _vector_top(query, domain=domain, top_k=top_k * 2)
    fused = _rrf_fuse([bm25_hits, vec_hits])[:top_k]
    ranked = _rerank(query, fused)
    if score_threshold is not None:
        ranked = [r for r in ranked if r.get("rrf_score", 0) >= score_threshold]
    return ranked


def retrieve_first_clause(query: str, domain: str,
                          min_rrf_score: float = 0.02) -> Optional[dict[str, Any]]:
    items = retrieve_clauses(query, domain=domain, top_k=1)
    if not items or items[0].get("rrf_score", 0) < min_rrf_score:
        return None
    return items[0]


def replace_domain_documents(domain: str, docs: list[dict[str, Any]]) -> None:
    """
    幂等重建某个 domain 的条款库。
    docs 元素必须包含：id/text/metadata(domain, doc_id, clause_no, title)
    """
    col = _get_collection()
    col.delete(where={"domain": domain})

    if not docs:
        invalidate_domain_cache(domain)
        return

    ids = [d["id"] for d in docs]
    documents = [d["text"] for d in docs]
    metadatas = [d["metadata"] for d in docs]
    embeddings = [_embed(text) for text in documents]

    col.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    invalidate_domain_cache(domain)


def invalidate_domain_cache(domain: Optional[str] = None) -> None:
    if domain is None:
        _BM25_CACHE.clear()
    else:
        _BM25_CACHE.pop(domain, None)


def _slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5]+", "-", text).strip("-").upper()
    return (s[:32] or "CLAUSE")


def parse_markdown_to_docs(markdown: str, domain: str, doc_id: str) -> list[dict[str, Any]]:
    """
    按 Markdown 二级标题切条款。
    如果没有 ##，则整篇作为一个条款。
    """
    lines = markdown.splitlines()
    chunks: list[str] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current:
                chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())

    docs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for idx, chunk in enumerate([c for c in chunks if c.strip()], start=1):
        chunk_lines = [ln for ln in chunk.splitlines() if ln.strip()]
        heading = chunk_lines[0].strip() if chunk_lines else doc_id
        title = heading[3:].strip() if heading.startswith("## ") else heading.lstrip("# ").strip()
        if not title:
            title = f"{doc_id} 条款 {idx}"

        clause_no = _slug(title)
        unique_id = f"{domain}:{doc_id}:{clause_no}"
        if unique_id in seen:
            unique_id = f"{unique_id}-{idx}"
        seen.add(unique_id)

        docs.append({
            "id": unique_id,
            "text": chunk.strip(),
            "metadata": {
                "domain": domain,
                "doc_id": doc_id,
                "clause_no": clause_no,
                "title": title,
            },
        })

    return docs