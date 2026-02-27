from huggingface_hub import InferenceClient


class HuggingFaceEmbeddings:
    def __init__(self, model: str, api_key: str, timeout: int = 60) -> None:
        self._model = model
        self._client = InferenceClient(provider="hf-inference", api_key=api_key, timeout=timeout)

    def embed_query(self, text: str) -> list[float]:
        try:
            data = self._client.feature_extraction(
                text,
                model=self._model,
                normalize=False,
            )
        except Exception as exc:
            raise RuntimeError(f"HF embeddings request failed: {exc}") from exc

        return self._normalize_vector(data)

    def _normalize_vector(self, data: object) -> list[float]:
        if hasattr(data, "tolist"):
            data = data.tolist()

        if isinstance(data, tuple):
            data = list(data)

        if isinstance(data, list) and data and all(isinstance(x, (int, float)) for x in data):
            return [float(x) for x in data]

        if isinstance(data, list) and data and all(isinstance(row, list) for row in data):
            rows = [row for row in data if isinstance(row, list) and row]
            if not rows:
                raise RuntimeError("HF embeddings response had empty token vectors")

            width = len(rows[0])
            if not all(len(row) == width for row in rows):
                raise RuntimeError("HF embeddings response had inconsistent vector lengths")

            sums = [0.0] * width
            for row in rows:
                for idx, value in enumerate(row):
                    sums[idx] += float(value)
            count = float(len(rows))
            return [value / count for value in sums]

        raise RuntimeError(f"Unexpected HF embeddings response format: {type(data).__name__}")
