import os


# DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PROMPT_GUARD_MODEL = os.getenv("PROMPT_GUARD_MODEL", "meta-llama/llama-prompt-guard-2-86m")

DEFAULT_CHAT_TEMPERATURE = 0.2
DEFAULT_SUMMARY_TEMPERATURE = 0.2
PLAYER_TEMPERATURE_RANDOMIZATION_ENABLED = False
