from sqlalchemy import text

from app.core.database import engine
from app.core.qdrant import get_qdrant_client


class HealthRepository:
    def ping_database(self) -> None:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def ping_qdrant(self) -> None:
        get_qdrant_client().get_collections()
