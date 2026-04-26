import os


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid {name} '{raw_value}'. Expected true or false.")


def _env_temperature(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        temperature = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} '{raw_value}'. Expected a number.") from exc

    if not 0.0 <= temperature <= 2.0:
        raise RuntimeError(f"Invalid {name} '{raw_value}'. Expected a value between 0.0 and 2.0.")
    return temperature


def _default_prompt_guard_model() -> str:
    prompt_guard_provider = os.getenv("PROMPT_GUARD_PROVIDER", "groq").strip().lower()
    if prompt_guard_provider == "mistral":
        return "mistral-moderation-2603"
    return "meta-llama/llama-prompt-guard-2-86m"


# DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b")
DEFAULT_CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", "groq").strip().lower()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PROMPT_GUARD_PROVIDER = os.getenv("PROMPT_GUARD_PROVIDER", "groq").strip().lower()
PROMPT_GUARD_MODEL = os.getenv("PROMPT_GUARD_MODEL", _default_prompt_guard_model())
PROMPT_GUARD_THRESHOLD = float(os.getenv("PROMPT_GUARD_THRESHOLD", "0.5"))

DEFAULT_CHAT_TEMPERATURE = _env_temperature("CHAT_TEMPERATURE", 0.2)
DEFAULT_SUMMARY_TEMPERATURE = _env_temperature("SUMMARY_TEMPERATURE", 0.2)
PLAYER_TEMPERATURE_RANDOMIZATION_ENABLED = _env_bool(
    "PLAYER_TEMPERATURE_RANDOMIZATION_ENABLED",
    True,
)

SUPPORTED_CHAT_PROVIDERS = {"groq", "gemini", "mistral"}
MISTRAL_MODEL_PREFIXES = ("mistral", "ministral", "codestral", "pixtral")


def resolve_chat_provider(model: str | None = None, provider: str | None = None) -> str:
    resolved_provider = (provider or "").strip().lower()
    if resolved_provider:
        if resolved_provider not in SUPPORTED_CHAT_PROVIDERS:
            raise RuntimeError(
                f"Unsupported CHAT_PROVIDER '{resolved_provider}'. "
                f"Expected one of: {', '.join(sorted(SUPPORTED_CHAT_PROVIDERS))}."
            )
        return resolved_provider

    normalized_model = (model or "").strip().lower()
    if normalized_model.startswith("gemini"):
        return "gemini"
    if normalized_model.startswith(MISTRAL_MODEL_PREFIXES):
        return "mistral"
    return DEFAULT_CHAT_PROVIDER


def get_required_chat_api_key(provider: str) -> tuple[str, str]:
    normalized_provider = resolve_chat_provider(provider=provider)
    api_key_by_provider = {
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }
    env_var_name = api_key_by_provider[normalized_provider]
    api_key = os.getenv(env_var_name)
    if not api_key:
        raise RuntimeError(f"Missing {env_var_name} in environment")
    return normalized_provider, api_key
