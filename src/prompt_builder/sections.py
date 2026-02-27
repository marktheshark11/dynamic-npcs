from .models import NPCProfile, RAGContext, PromptRequest
from .policy import PromptPolicy
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
        if profile.story_background:
            lines.append(f"Vad som har hänt: {profile.story_background}")
        # lines.append("“Svara kort. Max 1–2 meningar. Ingen självbiografi.”)")
        return "\n".join(lines)


class BehaviorSection:
    @staticmethod
    def render(policy: PromptPolicy) -> str:
        rules = policy.character_rules
        return "REGLER:\n" + "\n".join(f"- {rule}" for rule in rules if rule)


class ContextSection:
    @staticmethod
    def render(context: RAGContext) -> str:
        knowledge_block = format_bullet_list(context.knowledge_claims, "Ingen relevant kunskap")
        relation_block = format_bullet_list(context.relation_claims, "Inga relevanta relationer")
        return f"DETTA VET DU (Det behöver inte alltid vara relevant, håll dig till frågan):\n{knowledge_block}\n\nDINA RELATIONER:\n{relation_block}"


class TaskSection:
    @staticmethod
    def render(request: PromptRequest) -> str:
        suffix = request.answer_prefix or "SVAR:"
        return f"FRAGA: {request.question}\n{suffix}"
