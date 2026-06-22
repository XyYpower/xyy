import asyncio
import ipaddress
import re
import socket
import uuid
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.import_job import ExtractionDraft, ImportJob
from app.models.note import Note
from app.rag.extractor import extract_knowledge_points
from app.services import note_service, review_service


async def create_import_job(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_type: str,
    source_text: str,
    source_url: str | None = None,
) -> ImportJob:
    job = ImportJob(
        user_id=user_id,
        source_type=source_type,
        source_url=source_url,
        source_text=source_text,
        status="pending",
    )
    db.add(job)
    await db.flush()

    job.status = "processing"
    try:
        items = await extract_knowledge_points(source_text)
        drafts = [
            ExtractionDraft(import_job_id=job.id, title=item["title"], content=item["content"])
            for item in items
        ]
        db.add_all(drafts)
        job.status = "draft"
        await db.flush()
        await db.refresh(job)
        return job
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        await db.flush()
        await db.refresh(job)
        return job


async def get_import_jobs(db: AsyncSession, user_id: uuid.UUID) -> list[ImportJob]:
    result = await db.execute(
        select(ImportJob)
        .where(ImportJob.user_id == user_id)
        .order_by(ImportJob.created_at.desc())
    )
    return result.scalars().all()


async def get_import_job(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob | None:
    result = await db.execute(
        select(ImportJob)
        .options(selectinload(ImportJob.drafts))
        .where(ImportJob.id == job_id, ImportJob.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_drafts(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> list[ExtractionDraft]:
    job = await get_import_job(db, user_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    return sorted(job.drafts, key=lambda draft: draft.created_at)


async def update_draft(
    db: AsyncSession,
    user_id: uuid.UUID,
    draft_id: uuid.UUID,
    title: str | None = None,
    content: str | None = None,
    is_selected: bool | None = None,
) -> ExtractionDraft:
    draft = await _get_owned_draft(db, user_id, draft_id)
    if title is not None:
        draft.title = title
    if content is not None:
        draft.content = content
    if is_selected is not None:
        draft.is_selected = is_selected
    await db.flush()
    await db.refresh(draft)
    return draft


async def confirm_import(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> list[Note]:
    job = await get_import_job(db, user_id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
    if job.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import job is not ready to confirm")

    selected_drafts = [draft for draft in job.drafts if draft.is_selected and draft.note_id is None]
    notes: list[Note] = []
    for draft in selected_drafts:
        note = Note(
            user_id=user_id,
            title=draft.title,
            content=draft.content,
            source_type="imported",
            source_url=job.source_url,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        await note_service.embed_note(db, note)
        draft.note_id = note.id
        notes.append(note)

    job.status = "confirmed"
    await db.flush()
    return await _load_notes_for_output(db, [note.id for note in notes])


async def fetch_url_text(url: str) -> str:
    current_url = await _validate_public_http_url(url)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        for _ in range(4):
            try:
                response = await client.get(current_url, headers={"User-Agent": "KnowBase/1.0"})
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL fetch failed") from exc

            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Redirect location is missing")
                current_url = await _validate_public_http_url(urljoin(current_url, location))
                continue

            html = response.text
            break
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many redirects")

    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:8000]


async def _validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only http/https URLs are supported")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL userinfo is not allowed")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL port") from exc

    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL host could not be resolved") from exc

    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL host is not allowed")
    return url


async def _load_notes_for_output(db: AsyncSession, note_ids: list[uuid.UUID]) -> list[Note]:
    if not note_ids:
        return []
    result = await db.execute(
        select(Note)
        .options(selectinload(Note.category), selectinload(Note.tags))
        .where(Note.id.in_(note_ids))
    )
    by_id = {note.id: note for note in result.unique().scalars().all()}
    return [by_id[note_id] for note_id in note_ids if note_id in by_id]


async def _get_owned_draft(db: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID) -> ExtractionDraft:
    result = await db.execute(
        select(ExtractionDraft)
        .join(ExtractionDraft.import_job)
        .where(ExtractionDraft.id == draft_id, ImportJob.user_id == user_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction draft not found")
    return draft


async def quick_import_markdown(
    db: AsyncSession,
    user_id: uuid.UUID,
    markdown: str,
    category_id: uuid.UUID | None = None,
) -> list[Note]:
    """快速导入 Markdown：按 ## 标题拆分，直接创建笔记 + 生成复习卡片。"""
    items = _parse_markdown_sections(markdown)
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未找到可导入的内容，请确保使用 ## 标题分隔知识点")

    notes: list[Note] = []
    for item in items:
        note = Note(
            user_id=user_id,
            title=item["title"][:200],
            content=item["content"],
            source_type="imported",
            category_id=category_id,
        )
        db.add(note)
        await db.flush()
        await db.refresh(note)
        await note_service.embed_note(db, note)
        notes.append(note)

    return notes


def _parse_markdown_sections(markdown: str) -> list[dict[str, str]]:
    """按 Markdown 标题拆分内容。支持 ## 和 ### 级别。"""
    lines = markdown.strip().split("\n")
    sections: list[dict[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        # 匹配 ## 或 ### 开头的标题
        if line.startswith("## ") or line.startswith("### "):
            # 保存上一个 section
            if current_title and current_lines:
                content = "\n".join(current_lines).strip()
                if len(content) > 10:
                    sections.append({"title": current_title, "content": content})
            current_title = line.lstrip("#").strip()
            current_lines = []
        elif line.startswith("# "):
            # 一级标题作为分类标记，不作为知识点
            continue
        else:
            current_lines.append(line)

    # 最后一个 section
    if current_title and current_lines:
        content = "\n".join(current_lines).strip()
        if len(content) > 10:
            sections.append({"title": current_title, "content": content})

    # 如果没有标题，但内容足够长，作为单个知识点
    if not sections and markdown.strip():
        text = markdown.strip()
        if len(text) > 10:
            sections.append({"title": text[:50].split("\n")[0], "content": text})

    return sections[:50]  # 最多 50 个知识点
