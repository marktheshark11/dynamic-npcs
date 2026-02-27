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


class RulesSection:
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


class DetectiveContextSection:
    @staticmethod
    def render(request: PromptRequest) -> str:
        blocks = []

        if request.player_name or request.player_appearance:
            player_name = request.player_name or "Okand"
            player_appearance = request.player_appearance or "Okant"
            blocks.append(
                "DETTA VET DU OM DETEKTIVEN:\n"
                f"- Namn: {player_name}\n"
                f"- Utseende: {player_appearance}"
            )

        if request.recent_exchanges:
            lines = ["SENASTE SAMTAL I DENNA KONVERSATION:"]
            for exchange in request.recent_exchanges:
                player_text = exchange.get("player_text") or ""
                npc_text = exchange.get("npc_text") or ""
                lines.append(f"- DETEKTIVEN: {player_text}")
                lines.append(f"- DU: {npc_text}")
            blocks.append("\n".join(lines))

        if not blocks:
            return ""
        return "\n\n".join(blocks)


class TaskSection:
    @staticmethod
    def render(request: PromptRequest) -> str:
        suffix = request.answer_prefix or "SVAR:"
        return (
            "ANVANDARENS FRAGA (ORDAGRANT):\n"
            "<QUESTION>\n"
            f"{request.question}\n"
            "</QUESTION>\n"
            f"{suffix}"
        )
