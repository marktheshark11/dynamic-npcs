from .models import (
    NPCProfile,
    PromptBuildResult,
    PromptRequest,
    RAGContext,
)
from .policy import PromptPolicy
from .sections import (
    ContextSection,
    DetectiveContextSection,
    IdentitySection,
    RulesSection,
    TaskSection,
)


class PromptBuilder:
    def __init__(self, default_policy: PromptPolicy | None = None):
        self.default_policy = default_policy or PromptPolicy()

    def build(
        self,
        profile: NPCProfile,
        rag_context: RAGContext,
        request: PromptRequest,
        policy: PromptPolicy | None = None,
    ) -> PromptBuildResult:
        effective_policy = policy or self.default_policy

        identity_text = IdentitySection.render(profile)
        rules_text = RulesSection.render(effective_policy)
        world_context_text = ContextSection.render(rag_context)
        detective_context_text = DetectiveContextSection.render(request)
        task_text = TaskSection.render(request)

        system_parts = [identity_text, rules_text, world_context_text]
        if detective_context_text:
            system_parts.append(detective_context_text)
        system_text = "\n\n".join(system_parts)
        user_text = task_text
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ]
        flat_prompt = f"SYSTEM:\n{system_text}\n\n{user_text}"

        return PromptBuildResult(
            messages=messages,
            flat_prompt=flat_prompt,
            sections={
                "identity": identity_text,
                "rules": rules_text,
                "world_context": world_context_text,
                "detective_context": detective_context_text,
                "task": task_text,
            },
        )
