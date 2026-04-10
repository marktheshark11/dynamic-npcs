from db.repositories import UserRepo


class LocaleService:
    def __init__(self, driver):
        self.user_repo = UserRepo(driver)

    def get_player_locale(self, player_id: str | None) -> str:
        if not player_id:
            return "sv"
        return self.user_repo.get_locale_by_player_id(player_id)
