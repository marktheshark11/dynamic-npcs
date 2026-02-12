from langchain_community.embeddings import OllamaEmbeddings


class EmbeddingService:
    """Wrapper around the embedding model.

    Centralizes embedding creation so the model can be swapped
    without touching repositories or commands.
    """

    def __init__(self, model: OllamaEmbeddings) -> None:
        self._model = model

    def embed(self, text: str) -> list[float]:
        """Create an embedding vector for document content."""
        return self._model.embed_query(text)

    def embed_query(self, text: str) -> list[float]:
        """Create an embedding vector for a search query (with search prefix)."""
        return self._model.embed_query(
            f"Represent this sentence for searching relevant passages: {text}"
        )
