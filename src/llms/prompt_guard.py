import re

from groq import Groq


PROMPT_GUARD_MODEL = "meta-llama/llama-prompt-guard-2-86m"
PROMPT_GUARD_CHUNK_WORDS = 300
PROMPT_GUARD_THRESHOLD = 0.5


class PromptGuardValidationError(ValueError):
    pass


def _chunk_text(text: str, max_words: int = PROMPT_GUARD_CHUNK_WORDS) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def _extract_score(content: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", content)
    if not match:
        return None
    try:
        score = float(match.group(0))
    except ValueError:
        return None
    if 0.0 <= score <= 1.0:
        return score
    return None


def _classify_by_response(content: str) -> bool:
    score = _extract_score(content)
    if score is None:
        raise ValueError("Prompt Guard did not return a numeric score")
    return score >= PROMPT_GUARD_THRESHOLD


def _classify_chunk(client: Groq, chunk: str) -> bool:
    completion = client.chat.completions.create(
        model=PROMPT_GUARD_MODEL,
        temperature=0,
        max_tokens=16,
        messages=[{"role": "user", "content": chunk}],
    )
    response_content = completion.choices[0].message.content or ""
    return _classify_by_response(response_content)


def is_malicious(text: str) -> bool:
    client = Groq()
    chunks = _chunk_text(text)
    for chunk in chunks:
        if _classify_chunk(client, chunk):
            return True
    return False


def validate_safe_player_text(field_name: str, text: str) -> None:
    if is_malicious(text):
        raise PromptGuardValidationError(
            f"{field_name} innehåller otillåtet eller misstänkt innehåll. Ändra texten och försök igen."
        )


def validate_safe_player_profile(name: str, appearance: str) -> None:
    validate_safe_player_text("name", name)
    validate_safe_player_text("appearance", appearance)
