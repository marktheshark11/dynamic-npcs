from .config import DEFAULT_CHAT_MODEL, DEFAULT_CHAT_TEMPERATURE, resolve_chat_provider


def chat(
    message: str | None = None,
    model: str = DEFAULT_CHAT_MODEL,
    messages: list[dict[str, str]] | None = None,
    max_tokens: int = 1024,
    temperature: float = DEFAULT_CHAT_TEMPERATURE,
    provider: str | None = None,
) -> str:
    resolved_provider = resolve_chat_provider(model=model, provider=provider)

    if resolved_provider == "gemini":
        from .llm_gemini import chat as provider_chat
    elif resolved_provider == "mistral":
        from .llm_mistral import chat as provider_chat
    else:
        from .llm_groq import chat as provider_chat

    return provider_chat(
        message=message,
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
