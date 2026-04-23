import os

from dotenv import load_dotenv

from .config import DEFAULT_CHAT_MODEL, DEFAULT_CHAT_TEMPERATURE

load_dotenv()


def _extract_text_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
            continue
        item_type = getattr(item, "type", None)
        item_text = getattr(item, "text", None)
        if item_type == "text" and isinstance(item_text, str):
            parts.append(item_text)
    return "".join(parts)


def chat(
    message: str | None = None,
    model: str = DEFAULT_CHAT_MODEL,
    messages: list[dict[str, str]] | None = None,
    max_tokens: int = 1024,
    temperature: float = DEFAULT_CHAT_TEMPERATURE,
) -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY in environment")

    if messages is None:
        if message is None:
            raise ValueError("Either 'message' or 'messages' must be provided")
        messages = [{"role": "user", "content": message}]

    from mistralai.client import Mistral

    client = Mistral(api_key=api_key)
    completion = client.chat.complete(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _extract_text_content(completion.choices[0].message.content)
