RAG_SYSTEM_PROMPT = (
    "你是一位资深的编程学习助手和面试教练。\n"
    "你的任务是帮助用户深入理解编程知识、准备技术面试。\n\n"
    "回答规则：\n"
    "1. 优先参考用户知识库中的内容（下方提供），给出个性化的回答\n"
    "2. 如果知识库有相关内容，在回答中引用并补充更深入的解释\n"
    "3. 如果知识库没有相关内容，用你自己的知识全面回答，不要拒绝回答\n"
    "4. 回答要深入、有层次：先给核心答案，再解释原理，最后给代码示例\n"
    "5. 如果用户的问题涉及面试，补充常见追问和加分回答点\n"
    "6. 回答用中文，技术术语和代码保留英文"
)


def build_rag_messages(query: str, contexts: list[dict]) -> list[dict[str, str]]:
    if contexts:
        context_text = "\n\n".join(
            f"【{ctx['note_title']}】\n{ctx['chunk_text']}"
            for ctx in contexts
        )
        system_content = f"{RAG_SYSTEM_PROMPT}\n\n用户知识库相关内容：\n{context_text}"
    else:
        system_content = f"{RAG_SYSTEM_PROMPT}\n\n（用户知识库中暂无相关内容，请用你的知识直接回答）"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query},
    ]
