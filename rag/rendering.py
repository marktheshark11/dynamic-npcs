class Rendering:
    @staticmethod
    def render_claim_static(content, belief_in, openness):
        text = content
        b_value = abs(belief_in) if belief_in is not None else 1.0
        o_value = abs(openness) if openness is not None else 0.5
        opposite_signs = False
        if belief_in is not None and openness is not None:
            opposite_signs = (belief_in >= 0) != (openness >= 0)
        if b_value <= 0.2:
            text = f"Det är oklart ifall {text[0].lower()}{text[1:]}"
        elif b_value <= 0.6:
            text = f"Det är möjligt att {text[0].lower()}{text[1:]}"
        text = text.rstrip('.')
        if opposite_signs:
            if o_value >= 0.7:
                text = f"{text}, men det är du öppen med att neka."
            elif o_value >= 0.3:
                text = f"{text}, men det nekar du."
            else:
                text = f"{text}, vilket du undviker att prata om."
        else:
            if o_value >= 0.7:
                text = f"{text}, vilket du är bekväm att prata om."
            elif o_value <= 0.2:
                text = f"{text}, vilket du undviker att prata om."
            else:
                text = f"{text}."
        return text

    def build_prompt(self, npc_name, chain_metadata, question):
        non_relation = [c for c in chain_metadata if not c["is_relation"]]
        relation = [c for c in chain_metadata if c["is_relation"]]
        prompt = f"SYSTEM: Du ar {npc_name}. Svara kortfattat och hall dig till din karaktar.\n\n"
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
