class Rendering:
    @staticmethod
    def render_claim_static(c_id, content, prefix=None, suffix=None):
        if prefix:
            content = f"{prefix} {content[0].lower()}{content[1:]}" if content else content
        if c_id:
            text = f"<{c_id}> {content}"
        else:
            text = content
        if suffix:
            text = f"{text} [INSTRUKTION: {suffix}]"
        return text

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
