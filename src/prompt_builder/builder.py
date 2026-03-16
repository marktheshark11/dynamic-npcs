from .models import (
    NPCProfile,
    PromptBuildResult,
    PromptRequest,
    RAGContext,
)
from .sections import (
    ContextSection,
    DetectiveContextSection,
    IdentitySection,
    OutputFormatSection,
    RulesSection,
    StoryBackgroundSection,
    TaskSection,
)


class PromptBuilder:
    def build(
        self,
        profile: NPCProfile,
        rag_context: RAGContext,
        request: PromptRequest,
    ) -> PromptBuildResult:
        identity_text = IdentitySection.render(profile)
        rules_text = RulesSection.render()
        #print('rules_text:', rules_text)
        output_format_text = OutputFormatSection.render()
        #print('output_format_text:', output_format_text)
        story_background_text = StoryBackgroundSection.render(profile)
        world_context_text = ContextSection.render(rag_context)
        detective_context_text = DetectiveContextSection.render(request)
        task_text = TaskSection.render(request)

        # system_parts = [identity_text, rules_text, output_format_text]
        system_parts = []
        if identity_text:
            system_parts.append(identity_text)
        if story_background_text:
            system_parts.append(story_background_text)
        if rules_text:
            system_parts.append(rules_text)
        if output_format_text:
            system_parts.append(output_format_text)
        if world_context_text:
            system_parts.append(world_context_text)
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
                "output_format": output_format_text,
                "story_background": story_background_text,
                "world_context": world_context_text,
                "detective_context": detective_context_text,
                "task": task_text,
            },
        )
