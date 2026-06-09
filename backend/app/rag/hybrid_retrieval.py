"""Hybrid Retrieval：向量相似度 + 关键词全文搜索混合检索。"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag import embedding


async def hybrid_search(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    top_k: int = 6,
    vector_weight: float = 0.7,
) -> list[dict]:
    """混合检索：向量相似度 + PostgreSQL 全文搜索，加权合并结果。"""

    # 向量检索
    vector_results = await _vector_search(db, user_id, query, top_k=top_k * 2)

    # 关键词检索
    keyword_results = await _keyword_search(db, user_id, query, top_k=top_k * 2)

    # 合并去重并加权排序
    seen: dict[str, dict] = {}

    for i, r in enumerate(vector_results):
        key = f"{r['note_id']}:{r['chunk_text'][:50]}"
        vector_score = r["similarity"]
        rank_score = 1.0 - (i / max(len(vector_results), 1)) * 0.3
        seen[key] = {
            **r,
            "vector_score": vector_score,
            "keyword_score": 0.0,
            "combined_score": vector_score * vector_weight * rank_score,
        }

    for i, r in enumerate(keyword_results):
        key = f"{r['note_id']}:{r['chunk_text'][:50]}"
        keyword_score = r.get("rank", 0.5)
        rank_score = 1.0 - (i / max(len(keyword_results), 1)) * 0.3
        if key in seen:
            seen[key]["keyword_score"] = keyword_score
            seen[key]["combined_score"] += keyword_score * (1 - vector_weight) * rank_score
        else:
            seen[key] = {
                **r,
                "vector_score": 0.0,
                "keyword_score": keyword_score,
                "combined_score": keyword_score * (1 - vector_weight) * rank_score,
            }

    # 按 combined_score 降序排列
    results = sorted(seen.values(), key=lambda x: x["combined_score"], reverse=True)
    return results[:top_k]


async def _vector_search(db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 10) -> list[dict]:
    query_vector = embedding.vector_to_sql(await embedding.embed_text(query))
    result = await db.execute(
        text(
            """
            SELECT
                note_chunks.note_id,
                note_chunks.chunk_text,
                notes.title AS note_title,
                1 - (note_chunks.embedding <=> CAST(:query_vector AS vector)) AS similarity
            FROM note_chunks
            JOIN notes ON notes.id = note_chunks.note_id
            WHERE notes.user_id = :user_id
              AND note_chunks.embedding IS NOT NULL
            ORDER BY note_chunks.embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
            """
        ),
        {"user_id": user_id, "query_vector": query_vector, "top_k": top_k},
    )
    return [
        {
            "note_id": row.note_id,
            "chunk_text": row.chunk_text,
            "note_title": row.note_title,
            "similarity": float(row.similarity or 0),
        }
        for row in result
    ]


async def _keyword_search(db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 10) -> list[dict]:
    """使用 PostgreSQL 全文搜索（to_tsvector + plainto_tsquery）。"""
    # 提取关键词（简单分词：按空格拆分）
    keywords = [w.strip() for w in query.split() if len(w.strip()) >= 2]
    if not keywords:
        return []

    # 构造 OR 查询
    ts_query = " | ".join(keywords)

    result = await db.execute(
        text(
            """
            SELECT
                note_chunks.note_id,
                note_chunks.chunk_text,
                notes.title AS note_title,
                ts_rank(
                    to_tsvector('simple', note_chunks.chunk_text),
                    plainto_tsquery('simple', :query)
                ) AS rank
            FROM note_chunks
            JOIN notes ON notes.id = note_chunks.note_id
            WHERE notes.user_id = :user_id
              AND to_tsvector('simple', note_chunks.chunk_text) @@ plainto_tsquery('simple', :query)
            ORDER BY rank DESC
            LIMIT :top_k
            """
        ),
        {"user_id": user_id, "query": ts_query, "top_k": top_k},
    )
    return [
        {
            "note_id": row.note_id,
            "chunk_text": row.chunk_text,
            "note_title": row.note_title,
            "rank": float(row.rank or 0),
        }
        for row in result
    ]
