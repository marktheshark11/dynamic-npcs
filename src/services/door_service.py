from db.repositories import ConstantRepo, PlayerRepo


class DoorService:
    def __init__(self, driver):
        self.constant_repo = ConstantRepo(driver)
        self.player_repo = PlayerRepo(driver)

    def open_door(self, player_id: str, object_id: str, code: str | None = None) -> dict:
        door = self.constant_repo.get_door(object_id)
        if not door:
            raise ValueError("Door not found")

        self.player_repo.mark_seen_door(player_id, object_id)

        already_open = self.player_repo.has_opened_door(player_id, object_id)
        if already_open:
            return {
                "player_id": player_id,
                "object_id": door.object_id,
                "door_name": door.name,
                "opened": False,
                "already_open": True,
                "lock_type": door.lock_type,
                "required_item_id": door.required_item_id,
                "detail": "Dörren är redan öppnad.",
            }

        if not door.is_locked or door.lock_type == "none":
            self.player_repo.mark_opened_door(player_id, object_id)
            return {
                "player_id": player_id,
                "object_id": door.object_id,
                "door_name": door.name,
                "opened": True,
                "already_open": False,
                "lock_type": door.lock_type,
                "required_item_id": door.required_item_id,
                "detail": "Dörren öppnades.",
            }

        if door.lock_type == "item":
            if not door.required_item_id:
                return {
                    "player_id": player_id,
                    "object_id": door.object_id,
                    "door_name": door.name,
                    "opened": False,
                    "already_open": False,
                    "lock_type": door.lock_type,
                    "required_item_id": None,
                    "detail": "Dörren saknar konfigurerad nyckel.",
                }
            if not self.player_repo.has_item(player_id, door.required_item_id):
                return {
                    "player_id": player_id,
                    "object_id": door.object_id,
                    "door_name": door.name,
                    "opened": False,
                    "already_open": False,
                    "lock_type": door.lock_type,
                    "required_item_id": door.required_item_id,
                    "detail": "Du har inte rätt nyckel.",
                }
            self.player_repo.mark_opened_door(player_id, object_id)
            return {
                "player_id": player_id,
                "object_id": door.object_id,
                "door_name": door.name,
                "opened": True,
                "already_open": False,
                "lock_type": door.lock_type,
                "required_item_id": door.required_item_id,
                "detail": "Dörren öppnades med nyckel.",
            }

        submitted_code = (code or "").strip()
        if not submitted_code or submitted_code != (door.unlock_code or ""):
            return {
                "player_id": player_id,
                "object_id": door.object_id,
                "door_name": door.name,
                "opened": False,
                "already_open": False,
                "lock_type": door.lock_type,
                "required_item_id": None,
                "detail": "Fel kod.",
            }

        self.player_repo.mark_opened_door(player_id, object_id)
        return {
            "player_id": player_id,
            "object_id": door.object_id,
            "door_name": door.name,
            "opened": True,
            "already_open": False,
            "lock_type": door.lock_type,
            "required_item_id": None,
            "detail": "Dörren öppnades med kod.",
        }
