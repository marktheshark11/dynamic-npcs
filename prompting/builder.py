from .models import (
    NPCProfile,
    PromptBuildResult,
    PromptPolicy,
    PromptRequest,
    RAGContext,
)
from .sections import BehaviorSection, ContextSection, IdentitySection, TaskSection


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
        behavior_text = BehaviorSection.render(effective_policy)
        context_text = ContextSection.render(rag_context)
        task_text = TaskSection.render(request)

        system_text = f"{identity_text}\n\n{behavior_text}"
        user_text = f"{context_text}\n\n{task_text}"
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
                "behavior": behavior_text,
                "context": context_text,
                "task": task_text,
            },
        )
