import os
import logging
import warnings
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver

# Suppress Neo4j driver notifications (missing properties, etc.)
logging.getLogger("neo4j").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="neo4j")

from db.services.hf_embeddings import HuggingFaceEmbeddings


class Config:
    """Application configuration. Loads environment and creates shared resources."""

    def __init__(
        self,
        driver: Driver,
        embed_model: HuggingFaceEmbeddings,
        pipeline_id: str,
    ) -> None:
        self.driver = driver
        self.embed_model = embed_model
        self.pipeline_id = pipeline_id

    @classmethod
    def from_env(cls) -> "Config":
        """Create Config from .env file."""
        load_dotenv()

        db_uri = os.getenv("NEO4J_URI")
        db_user = os.getenv("NEO4J_USER")
        db_password = os.getenv("NEO4J_PASSWORD")

        if not db_uri or not db_user or not db_password:
            raise RuntimeError(
                "Saknar NEO4J_URI, NEO4J_USER eller NEO4J_PASSWORD i .env"
            )

        hf_token = os.getenv("HF_TOKEN")
        if not hf_token:
            raise RuntimeError("Missing HF_TOKEN in environment")

        driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
        embedding_model = os.getenv("EMBED_MODEL", "mixedbread-ai/mxbai-embed-large-v1")
        embed_model = HuggingFaceEmbeddings(model=embedding_model, api_key=hf_token)
        pipeline_id = os.getenv("CHAT_PIPELINE", "default_rag")

        return cls(
            driver=driver,
            embed_model=embed_model,
            pipeline_id=pipeline_id,
        )

    def close(self) -> None:
        """Close the database driver."""
        self.driver.close()
