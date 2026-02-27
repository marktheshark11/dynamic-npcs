import os

from dotenv import load_dotenv
from google import genai

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
    model: str = "gemini-2.0-flash",
    messages: list[dict[str, str]] | None = None,
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
    )
    return response.text or ""
