from app.repositories.health_repository import HealthRepository


class HealthService:
    def __init__(self) -> None:
        self._repository = HealthRepository()

    def check(self) -> dict[str, str]:
        return {"status": "ok"}

    def check_database(self) -> dict[str, str]:
        self._repository.ping_database()
        return {"status": "ok", "database": "connected"}

    def check_qdrant(self) -> dict[str, str]:
        self._repository.ping_qdrant()
        return {"status": "ok", "qdrant": "connected"}
