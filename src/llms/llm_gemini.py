import os

from dotenv import load_dotenv
from google import genai

from .config import DEFAULT_CHAT_TEMPERATURE, DEFAULT_GEMINI_MODEL

load_dotenv()


def _messages_to_text(messages: list[dict[str, str]]) -> str:
    lines = []
    for item in messages:
        role = item.get("role", "user").upper()
        content = item.get("content", "")
        lines.append(f"[{role}]\n{content}")
    return "\n\n".join(lines)


def chat(
    message: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
    messages: list[dict[str, str]] | None = None,
    max_tokens: int = 1024,
    temperature: float = DEFAULT_CHAT_TEMPERATURE,
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment")

    if messages is None:
        if message is None:
            raise ValueError("Either 'message' or 'messages' must be provided")
        prompt_text = message
    else:
        prompt_text = _messages_to_text(messages)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt_text,
        config={
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        },
    )
    return response.text or ""
