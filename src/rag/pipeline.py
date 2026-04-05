from pipelines.rag_workflow import ConfigurableRAGWorkflow


class RAGPipeline(ConfigurableRAGWorkflow):
    """Compatibility shim for older imports.

    The full workflow now lives under `pipelines/`, while `rag/` holds
    retrieval-related building blocks.
    """
