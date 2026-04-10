from .base import BaseRepository
from ..models import User

# Fallback admin user ID
ADMIN_USER_ID = "user_1"


class UserRepo(BaseRepository):
    """CRUD operations for USER nodes."""

    SUPPORTED_LOCALES = {"sv", "en"}

    @classmethod
    def _normalize_locale(cls, locale: str | None) -> str:
        normalized = (locale or "sv").strip().lower()
        if normalized not in cls.SUPPORTED_LOCALES:
            raise ValueError("Unsupported locale")
        return normalized

    def get_admin(self) -> User | None:
        """Get the admin user (fallback user). Returns None if admin doesn't exist."""
        return self.get_by_id(ADMIN_USER_ID)

    def get_by_id_or_admin(self, user_id: str | None) -> User | None:
        """Get user by ID, or return admin user as fallback if user_id is None or not found."""
        if user_id:
            user = self.get_by_id(user_id)
            if user:
                return user
        # Fallback to admin user
        return self.get_admin()

    def _next_user_id(self) -> str:
        record = self._run_single(
            "MATCH (u:USER) "
            "WITH CASE "
            "WHEN u.user_id STARTS WITH 'user_' THEN toInteger(split(u.user_id, '_')[1]) "
            "ELSE NULL "
            "END AS numeric_id "
            "RETURN coalesce(max(numeric_id), 0) + 1 AS next_id"
        )
        next_id = 1 if not record else record["next_id"]
        return f"user_{next_id}"

    def register(self, username: str, password: str, locale: str = "sv") -> User | None:
        """Register a new user. Returns User if successful, None if username already exists."""
        # Check if username already exists
        existing = self._run_single(
            "MATCH (u:USER {username: $username}) "
            "RETURN u.user_id AS user_id",
            username=username,
        )
        if existing:
            return None

        normalized_locale = self._normalize_locale(locale)
        user_id = self._next_user_id()
        self._run(
            "CREATE (u:USER {user_id: $user_id, username: $username, password: $password, locale: $locale})",
            user_id=user_id,
            username=username,
            password=password,
            locale=normalized_locale,
        )
        return User(user_id=user_id, username=username, password=password, locale=normalized_locale)

    def login(self, username: str, password: str) -> User | None:
        """Login user. Returns User if credentials match, None otherwise."""
        record = self._run_single(
            "MATCH (u:USER {username: $username, password: $password}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password, coalesce(u.locale, 'sv') AS locale",
            username=username,
            password=password,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
            locale=record.get("locale") or "sv",
        )

    def get_by_id(self, user_id: str) -> User | None:
        """Get user by user_id."""
        record = self._run_single(
            "MATCH (u:USER {user_id: $user_id}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password, coalesce(u.locale, 'sv') AS locale",
            user_id=user_id,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
            locale=record.get("locale") or "sv",
        )

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        record = self._run_single(
            "MATCH (u:USER {username: $username}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password, coalesce(u.locale, 'sv') AS locale",
            username=username,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
            locale=record.get("locale") or "sv",
        )

    def list_all(self) -> list[User]:
        """List all users."""
        records = self._run(
            "MATCH (u:USER) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password, coalesce(u.locale, 'sv') AS locale "
            "ORDER BY u.user_id"
        )
        return [
            User(
                user_id=r["user_id"],
                username=r["username"],
                password=r["password"],
                locale=r.get("locale") or "sv",
            )
            for r in records
        ]

    def update(
        self,
        user_id: str,
        username: str | None = None,
        password: str | None = None,
        locale: str | None = None,
    ) -> bool:
        """Update user. Returns True if successful."""
        set_clauses = []
        params: dict[str, str] = {"user_id": user_id}

        if username is not None:
            # Check if new username already exists on another user
            existing = self._run_single(
                "MATCH (u:USER {username: $new_username}) "
                "WHERE u.user_id <> $user_id "
                "RETURN u.user_id AS user_id",
                new_username=username,
                user_id=user_id,
            )
            if existing:
                return False
            set_clauses.append("u.username = $username")
            params["username"] = username

        if password is not None:
            set_clauses.append("u.password = $password")
            params["password"] = password

        if locale is not None:
            set_clauses.append("u.locale = $locale")
            params["locale"] = self._normalize_locale(locale)

        if not set_clauses:
            return False

        query = f"MATCH (u:USER {{user_id: $user_id}}) SET {', '.join(set_clauses)} RETURN u"
        record = self._run_single(query, **params)
        return record is not None

    def set_locale(self, user_id: str, locale: str) -> bool:
        """Update only the user locale."""
        normalized_locale = self._normalize_locale(locale)
        record = self._run_single(
            "MATCH (u:USER {user_id: $user_id}) "
            "SET u.locale = $locale "
            "RETURN u.user_id AS user_id",
            user_id=user_id,
            locale=normalized_locale,
        )
        return record is not None

    def delete(self, user_id: str) -> bool:
        """Delete user. Returns True if successful."""
        record = self._run_single(
            "MATCH (u:USER {user_id: $user_id}) "
            "RETURN u.user_id AS user_id",
            user_id=user_id,
        )
        if not record:
            return False

        self._run(
            "MATCH (u:USER {user_id: $user_id}) "
            "DETACH DELETE u",
            user_id=user_id,
        )
        return True
