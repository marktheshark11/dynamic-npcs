from .base import BaseRepository
from ..models import User

# Fallback admin user ID
ADMIN_USER_ID = "user_1"


class UserRepo(BaseRepository):
    """CRUD operations for USER nodes."""

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

    def register(self, username: str, password: str) -> User | None:
        """Register a new user. Returns User if successful, None if username already exists."""
        # Check if username already exists
        existing = self._run_single(
            "MATCH (u:USER {username: $username}) "
            "RETURN u.user_id AS user_id",
            username=username,
        )
        if existing:
            return None

        user_id = self._next_user_id()
        self._run(
            "CREATE (u:USER {user_id: $user_id, username: $username, password: $password})",
            user_id=user_id,
            username=username,
            password=password,
        )
        return User(user_id=user_id, username=username, password=password)

    def login(self, username: str, password: str) -> User | None:
        """Login user. Returns User if credentials match, None otherwise."""
        record = self._run_single(
            "MATCH (u:USER {username: $username, password: $password}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password",
            username=username,
            password=password,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
        )

    def get_by_id(self, user_id: str) -> User | None:
        """Get user by user_id."""
        record = self._run_single(
            "MATCH (u:USER {user_id: $user_id}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password",
            user_id=user_id,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
        )

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        record = self._run_single(
            "MATCH (u:USER {username: $username}) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password",
            username=username,
        )
        if not record:
            return None
        return User(
            user_id=record["user_id"],
            username=record["username"],
            password=record["password"],
        )

    def list_all(self) -> list[User]:
        """List all users."""
        records = self._run(
            "MATCH (u:USER) "
            "RETURN u.user_id AS user_id, u.username AS username, u.password AS password "
            "ORDER BY u.user_id"
        )
        return [
            User(
                user_id=r["user_id"],
                username=r["username"],
                password=r["password"],
            )
            for r in records
        ]

    def update(self, user_id: str, username: str | None = None, password: str | None = None) -> bool:
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

        if not set_clauses:
            return False

        query = f"MATCH (u:USER {{user_id: $user_id}}) SET {', '.join(set_clauses)} RETURN u"
        record = self._run_single(query, **params)
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
