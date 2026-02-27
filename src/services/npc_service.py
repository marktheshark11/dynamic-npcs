class NPCService:
    def __init__(self, driver):
        self.driver = driver

    def list_npcs(self):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (n:NPC) "
                "RETURN n.id AS id, n.name AS name, n.age AS age "
                "ORDER BY n.name"
            )
            return [
                {"id": r["id"], "name": r["name"], "age": r.get("age")}
                for r in result
            ]

    def get_npc_by_id(self, npc_id):
        with self.driver.session() as session:
            record = session.run(
                "MATCH (n:NPC {id: $npc_id}) "
                "RETURN n.id AS id, n.name AS name, n.age AS age, "
                "n.personality AS personality, n.backstory AS backstory "
                "LIMIT 1",
                npc_id=npc_id,
            ).single()
            if not record:
                return None
            return {
                "id": record["id"],
                "name": record["name"],
                "age": record.get("age"),
                "personality": record.get("personality"),
                "backstory": record.get("backstory"),
            }

    def get_npc_name(self, npc_id):
        npc = self.get_npc_by_id(npc_id)
        if not npc:
            return None
        return npc["name"]
