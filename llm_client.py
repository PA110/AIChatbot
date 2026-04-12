"""
LLM Client — Wraps Anthropic Claude API.
Injects retrieved context into the system prompt for grounded answers.
"""
import os
from typing import List, Dict, Generator
import anthropic

SYSTEM_PROMPT = """You are a helpful internal company assistant with access to our official documentation.

Your job is to answer employee questions accurately using ONLY the provided context from our knowledge base.

Rules:
- Answer based on the provided context only. Do not make up information.
- If the context does not contain enough information to answer, say so clearly and suggest the employee contact the relevant department (HR, IT, etc.).
- Always cite which document(s) your answer comes from at the end of your response using the format: [Source: Document Name].
- Be concise, professional, and friendly.
- For policy questions, be precise — employees rely on this for compliance.
- Format your response with clear headings or bullet points when the answer has multiple parts.
"""

def build_context_block(chunks: List[Dict]) -> str:
    if not chunks:
        return "No relevant documents found in the knowledge base."
    lines = ["RELEVANT KNOWLEDGE BASE EXCERPTS:\n"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[Excerpt {i} — Source: {chunk['source']} | Relevance: {chunk['score']:.3f}]")
        lines.append(chunk["text"])
        lines.append("")
    return "\n".join(lines)


def chat(
    query: str,
    chunks: List[Dict],
    history: List[Dict],
    model: str = "claude-sonnet-4-20250514",
    stream: bool = True,
) -> Generator[str, None, None]:
    """
    Yield response tokens. history is list of {role, content} dicts.
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

    context = build_context_block(chunks)
    system  = SYSTEM_PROMPT + "\n\n" + context

    messages = history + [{"role": "user", "content": query}]

    if stream:
        with client.messages.stream(
            model=model,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream_obj:
            for text in stream_obj.text_stream:
                yield text
    else:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        yield response.content[0].text


def chat_no_stream(query: str, chunks: List[Dict], history: List[Dict]) -> str:
    return "".join(chat(query, chunks, history, stream=False))
