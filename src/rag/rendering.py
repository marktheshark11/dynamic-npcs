class Rendering:
    @staticmethod
    def render_claim_static(
        c_id: str | None,
        content: str,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> str:
        text = content or ""

        if prefix and text:
            text = f"{prefix} {text[0].lower()}{text[1:]}"

        parts: list[str] = []
        if c_id:
            parts.append(f"<{c_id}>")
        if text:
            parts.append(text)
        if suffix:
            parts.append(suffix)

        return " ".join(parts)

    def build_prompt(self, npc_name, chain_metadata, question):
        non_relation = [c for c in chain_metadata if not c["is_relation"]]
        relation = [c for c in chain_metadata if c["is_relation"]]
        prompt = f"SYSTEM: Du är {npc_name}. Svara kortfattat och håll dig till din karaktär.\n\n"
        prompt += "DIN KUNSKAP OM FRÅGAN:\n"
        if non_relation:
            for c in non_relation:
                prompt += f"- {c['content']}\n"
        else:
            prompt += "- (Ingen relevant kunskap)\n"
        prompt += "\nDINA RELATIONER:\n"
        if relation:
            for c in relation:
                prompt += f"- {c['content']}\n"
        else:
            prompt += "- (Inga relevanta relationer)\n"
        prompt += f"\nFRÅGA: {question}\n{npc_name.upper()}:"
        return prompt
