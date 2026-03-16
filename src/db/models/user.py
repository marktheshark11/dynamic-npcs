from dataclasses import dataclass


@dataclass
class User:
    user_id: str
    username: str
    password: str

    def display_str(self) -> str:
        return f"ID: {self.user_id}, Användarnamn: {self.username}"

    def short_str(self) -> str:
        return f"ID: {self.user_id}, Användarnamn: {self.username}"
