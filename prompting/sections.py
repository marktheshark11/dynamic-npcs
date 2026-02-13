from .models import NPCProfile, PromptPolicy, RAGContext, PromptRequest
from .templates import format_bullet_list


class IdentitySection:
    @staticmethod
    def render(profile: NPCProfile) -> str:
        role_name = profile.roleplay_as or profile.name
        lines = [f"Du ar {role_name}."]
        if profile.personality:
            lines.append(f"Personlighet: {profile.personality}")
        if profile.backstory:
            lines.append(f"Bakgrund: {profile.backstory}")
        return "\n".join(lines)


class BehaviorSection:
    @staticmethod
    def render(policy: PromptPolicy) -> str:
        rules = [
            policy.brevity_instruction,
            policy.character_instruction,
            policy.truthfulness_instruction,
        ]
        rules.extend(policy.extra_rules)
        return "REGLER:\n" + "\n".join(f"- {rule}" for rule in rules if rule)


class ContextSection:
    @staticmethod
    def render(context: RAGContext) -> str:
        knowledge_block = format_bullet_list(context.knowledge_claims, "Ingen relevant kunskap")
        relation_block = format_bullet_list(context.relation_claims, "Inga relevanta relationer")
        return f"DIN KUNSKAP OM FRAGAN:\n{knowledge_block}\n\nDINA RELATIONER:\n{relation_block}"


class TaskSection:
    @staticmethod
    def render(request: PromptRequest) -> str:
        suffix = request.answer_prefix or "SVAR:"
        return f"FRAGA: {request.question}\n{suffix}"
