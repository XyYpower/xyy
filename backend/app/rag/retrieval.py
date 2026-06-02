import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag import embedding


async def search_similar(db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 5) -> list[dict]:
    """基于当前用户的 note_chunks 做相似度检索。"""
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
