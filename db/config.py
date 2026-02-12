import os
from dotenv import load_dotenv
from neo4j import GraphDatabase, Driver
from langchain_community.embeddings import OllamaEmbeddings


class Config:
    """Application configuration. Loads environment and creates shared resources."""

    def __init__(self, driver: Driver, embed_model: OllamaEmbeddings) -> None:
        self.driver = driver
        self.embed_model = embed_model

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

        driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
        embed_model = OllamaEmbeddings(model="mxbai-embed-large")

        return cls(driver=driver, embed_model=embed_model)

    def close(self) -> None:
        """Close the database driver."""
        self.driver.close()
