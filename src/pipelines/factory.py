from typing import Any

from .base import ChatPipeline
from .default_rag import DefaultRAGPipeline
from .direct_rag import DirectRAGPipeline
from .wide_select_rag import WideSelectRAGPipeline


def build_pipelines(
    driver: Any,
    embed_model: Any,
) -> dict[str, ChatPipeline]:
    pipelines = [
        DefaultRAGPipeline(driver, embed_model),
        DirectRAGPipeline(driver, embed_model),
        WideSelectRAGPipeline(driver, embed_model),
    ]
    return {pipeline.pipeline_id: pipeline for pipeline in pipelines}


def get_pipeline(
    pipeline_id: str,
    driver: Any,
    embed_model: Any,
) -> ChatPipeline:
    pipelines = build_pipelines(driver=driver, embed_model=embed_model)
    pipeline = pipelines.get(pipeline_id)
    if pipeline is None:
        available = ", ".join(sorted(pipelines)) or "(inga)"
        raise RuntimeError(
            f"Unknown pipeline '{pipeline_id}'. Available pipelines: {available}"
        )
    return pipeline
