import os
import re
import sys

from .chat import chat as llm_chat
from .config import PROMPT_GUARD_MODEL, PROMPT_GUARD_PROVIDER, PROMPT_GUARD_THRESHOLD

PROMPT_GUARD_CHUNK_WORDS = 300


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


def _classify_chunk_with_chat_model(chunk: str) -> bool:
    print(
        f"[PromptGuard] provider={PROMPT_GUARD_PROVIDER} model={PROMPT_GUARD_MODEL} mode=chat-score",
        file=sys.stderr,
    )
    response_content = llm_chat(
        messages=[{"role": "user", "content": chunk}],
        model=PROMPT_GUARD_MODEL,
        provider=PROMPT_GUARD_PROVIDER,
        temperature=0,
        max_tokens=16,
    )
    return _classify_by_response(response_content)


def _get_category_score(category_scores: object, category_name: str) -> float | None:
    if isinstance(category_scores, dict):
        score = category_scores.get(category_name)
        if isinstance(score, (int, float)):
            return float(score)
        return None

    score = getattr(category_scores, category_name, None)
    if isinstance(score, (int, float)):
        return float(score)
    return None


def _classify_chunk_with_mistral_moderation(chunk: str) -> bool:
    from mistralai.client import Mistral

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MISTRAL_API_KEY in environment")

    print(
        f"[PromptGuard] provider={PROMPT_GUARD_PROVIDER} model={PROMPT_GUARD_MODEL} mode=mistral-moderation",
        file=sys.stderr,
    )
    client = Mistral(api_key=api_key)
    response = client.classifiers.moderate(
        model=PROMPT_GUARD_MODEL,
        inputs=[chunk],
    )
    results = getattr(response, "results", None) or []
    if not results:
        raise ValueError("Prompt Guard did not return moderation results")

    first_result = results[0]
    category_scores = getattr(first_result, "category_scores", None)
    score = _get_category_score(category_scores, "jailbreaking")
    if score is None:
        raise ValueError("Prompt Guard did not return a jailbreaking score")
    print(
        f"[PromptGuard] jailbreaking_score={score:.4f} threshold={PROMPT_GUARD_THRESHOLD:.4f}",
        file=sys.stderr,
    )
    return score >= PROMPT_GUARD_THRESHOLD


def _classify_chunk(chunk: str) -> bool:
    if PROMPT_GUARD_PROVIDER == "mistral":
        return _classify_chunk_with_mistral_moderation(chunk)
    return _classify_chunk_with_chat_model(chunk)


def is_malicious(text: str) -> bool:
    chunks = _chunk_text(text)
    for chunk in chunks:
        if _classify_chunk(chunk):
            return True
    return False


def validate_safe_player_text(field_name: str, text: str) -> None:
    if is_malicious(text):
        raise PromptGuardValidationError(
            f"{field_name} innehåller otillåtet eller misstänkt innehåll. Ändra texten och försök igen."
        )


def validate_safe_player_profile(name: str, appearance: str | None) -> None:
    validate_safe_player_text("name", name)
    if appearance is not None:
        validate_safe_player_text("appearance", appearance)
