from dataclasses import dataclass


@dataclass
class User:
    user_id: str
    username: str
    password: str
    locale: str = "sv"
    created_at: str | None = None

    def display_str(self) -> str:
        return f"ID: {self.user_id}, Användarnamn: {self.username}, Språk: {self.locale}"

    def short_str(self) -> str:
        return f"ID: {self.user_id}, Användarnamn: {self.username}, Språk: {self.locale}"
