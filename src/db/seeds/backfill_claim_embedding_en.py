from db.config import Config
from db.services import EmbeddingService


FETCH_QUERY = """
MATCH (c:CLAIM)
WHERE c.content_en IS NOT NULL
  AND trim(c.content_en) <> ''
  AND c.embedding_en IS NULL
RETURN c.claim_id AS claim_id, c.content_en AS content_en
ORDER BY c.claim_id
"""

UPDATE_QUERY = """
UNWIND $rows AS row
MATCH (c:CLAIM {claim_id: row.claim_id})
SET c.embedding_en = row.embedding_en
RETURN count(c) AS updated_count
"""


def _fetch_claim_rows(config: Config) -> list[dict[str, str]]:
    with config.driver.session() as session:
        result = session.run(FETCH_QUERY)
        return [
            {
                "claim_id": record["claim_id"],
                "content_en": record["content_en"],
            }
            for record in result
        ]


def _update_embeddings(config: Config, rows: list[dict[str, object]]) -> int:
    if not rows:
        return 0
    with config.driver.session() as session:
        record = session.run(UPDATE_QUERY, rows=rows).single()
        return 0 if not record else int(record["updated_count"])


def main() -> None:
    config = Config.from_env()
    embedding_service = EmbeddingService(config.embed_model)

    try:
        claim_rows = _fetch_claim_rows(config)
        total = len(claim_rows)
        print(f"Found {total} claims missing embedding_en")
        if not claim_rows:
            return

        updated_total = 0
        failed_claim_ids: list[str] = []
        batch_size = 25

        for start in range(0, total, batch_size):
            batch = claim_rows[start:start + batch_size]
            update_rows: list[dict[str, object]] = []

            for claim in batch:
                claim_id = claim["claim_id"]
                content_en = claim["content_en"]
                try:
                    embedding_en = embedding_service.embed(content_en)
                    update_rows.append(
                        {
                            "claim_id": claim_id,
                            "embedding_en": embedding_en,
                        }
                    )
                except Exception as exc:
                    failed_claim_ids.append(claim_id)
                    print(f"Failed to embed {claim_id}: {exc}")

            updated_count = _update_embeddings(config, update_rows)
            updated_total += updated_count
            end = min(start + batch_size, total)
            print(f"Processed {end}/{total} claims; updated {updated_total}")

        print(f"Backfill complete. Updated {updated_total} claims.")
        if failed_claim_ids:
            print("Failed claim_ids:")
            for claim_id in failed_claim_ids:
                print(f"- {claim_id}")
    finally:
        config.close()


if __name__ == "__main__":
    main()
