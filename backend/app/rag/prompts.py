RAG_SYSTEM_PROMPT = (
    "你是 KnowBase AI 助手。根据用户的知识库内容回答问题。"
    "回答时引用来源，注明引用了哪些知识点。"
    "如果知识库中没有相关内容，如实说明，不要编造。"
    "回答用中文，技术术语保留英文。"
)


def build_rag_messages(query: str, contexts: list[dict]) -> list[dict[str, str]]:
    context_text = "\n\n".join(
        f"【知识点：{context['note_title']}】\n{context['chunk_text']}"
        for context in contexts
    ) or "没有检索到相关知识点。"
    return [
        {"role": "system", "content": f"{RAG_SYSTEM_PROMPT}\n\n参考知识库内容：\n{context_text}"},
        {"role": "user", "content": query},
    ]
