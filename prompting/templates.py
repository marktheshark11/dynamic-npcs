def format_bullet_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"- ({empty_text})"
    return "\n".join(f"- {item}" for item in items)
