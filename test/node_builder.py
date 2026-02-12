from neo4j import Driver, GraphDatabase
from langchain_community.embeddings import OllamaEmbeddings
from dotenv import load_dotenv
import os

class NodeBuilder:
  def __init__(self, driver: Driver, embed_model: OllamaEmbeddings) -> None:
    self.driver = driver
    self.embed_model = embed_model

  def create_embedding(self, text):
    return self.embed_model.embed_query(text)

  def get_next_claim_id(self):
    """Hämta nästa tillgängliga claim ID (C1, C2, C3, etc.)"""
    with self.driver.session() as session:
        # Hämta alla befintliga claim_id som börjar med 'C'
        query = """
        MATCH (c:CLAIM)
        WHERE c.claim_id IS NOT NULL AND c.claim_id STARTS WITH 'C'
        RETURN c.claim_id AS claim_id
        ORDER BY c.claim_id
        """
        result = session.run(query)
        existing_ids = [record['claim_id'] for record in result]
        
        # Hitta nästa tillgängliga nummer
        if not existing_ids:
            return 'C1'
        
        # Extrahera nummer från befintliga IDs (C1 -> 1, C2 -> 2, etc.)
        numbers = []
        for claim_id in existing_ids:
            try:
                num = int(claim_id[1:])  # Ta bort 'C' och konvertera till int
                numbers.append(num)
            except ValueError:
                continue
        
        if not numbers:
            return 'C1'
        
        # Returnera nästa nummer
        next_num = max(numbers) + 1
        return f'C{next_num}'

  def create_npc_node(self, id, name, age, personality):
    with self.driver.session() as session:
        query = "MERGE (npc:NPC {id: $id, name: $name, age: $age, personality: $personality})"
        session.run(query, id=id, name=name, age=age, personality=personality)
        print(f"\n✓ NPC '{name}' skapad")

  def delete_npc(self, id):
    with self.driver.session() as session:
        query = "MATCH (npc:NPC {id: $id}) DELETE npc"
        session.run(query, id=id)
        print(f"\n✓ NPC med id '{id}' borttagen")

  def edit_npc(self, id, name=None, age=None, personality=None):
    with self.driver.session() as session:
        set_clauses = []
        params = {"id": id}
        
        if name is not None:
            set_clauses.append("npc.name = $name")
            params["name"] = name
        if age is not None:
            set_clauses.append("npc.age = $age")
            params["age"] = age
        if personality is not None:
            set_clauses.append("npc.personality = $personality")
            params["personality"] = personality
        
        if set_clauses:
            query = f"MATCH (npc:NPC {{id: $id}}) SET {', '.join(set_clauses)} RETURN npc"
            result = session.run(query, **params)
            if result.single():
                print(f"\n✓ NPC med id '{id}' uppdaterad")
            else:
                print(f"\n✗ NPC med id '{id}' hittades inte")
        else:
            print(f"\n✗ Inga ändringar angivna")

  def create_claim(self, content, relation_type=None):
    embedding = self.create_embedding(content)
    claim_id = self.get_next_claim_id()

    with self.driver.session() as session:
        if relation_type:
            query = "CREATE (c:CLAIM {claim_id: $claim_id, content: $content, type: $relation_type, embedding: $embedding}) RETURN id(c) AS neo_id"
            result = session.run(query, claim_id=claim_id, content=content, relation_type=relation_type, embedding=embedding)
        else:
            query = "CREATE (c:CLAIM {claim_id: $claim_id, content: $content, embedding: $embedding}) RETURN id(c) AS neo_id"
            result = session.run(query, claim_id=claim_id, content=content, embedding=embedding)
        
        record = result.single()
        neo_id = record["neo_id"] if record else None
        print(f"\n✓ CLAIM {claim_id} skapad: '{content}'")
        return claim_id

  def list_all_npcs(self):
    with self.driver.session() as session:
        query = "MATCH (npc:NPC) RETURN npc.id AS id, npc.name AS name, npc.age AS age, npc.personality AS personality ORDER BY npc.id"
        result = session.run(query)
        npcs = []
        for record in result:
            npcs.append({
                'id': record['id'],
                'name': record['name'],
                'age': record['age'],
                'personality': record['personality']
            })
        return npcs

  def list_all_claims(self):
    with self.driver.session() as session:
        query = "MATCH (c:CLAIM) RETURN c.claim_id AS claim_id, c.content AS content, c.type AS type ORDER BY c.claim_id"
        result = session.run(query)
        claims = []
        for record in result:
            claims.append({
                'claim_id': record['claim_id'],
                'content': record['content'],
                'type': record['type']
            })
        return claims

  def delete_claim(self, claim_id):
    """Ta bort en CLAIM och alla HAS_OPINION relationer som pekar på den.
    
    Args:
        claim_id: claim_id för CLAIM-noden som ska tas bort (t.ex. 'C1', 'C2')
    """
    with self.driver.session() as session:
        # Hämta info om claimen först
        info_query = """
        MATCH (c:CLAIM {claim_id: $claim_id})
        OPTIONAL MATCH ()-[r:HAS_OPINION]->(c)
        RETURN c.content AS content, count(r) AS opinion_count
        """
        result = session.run(info_query, claim_id=claim_id)
        record = result.single()
        
        if not record or not record["content"]:
            print(f"\n✗ Ingen CLAIM hittades med ID {claim_id}")
            return False
        
        content = record["content"]
        opinion_count = record["opinion_count"]
        
        # Ta bort alla HAS_OPINION relationer och sedan claimen
        delete_query = """
        MATCH (c:CLAIM {claim_id: $claim_id})
        OPTIONAL MATCH ()-[r:HAS_OPINION]->(c)
        DELETE r, c
        """
        session.run(delete_query, claim_id=claim_id)
        
        print(f"\n✓ CLAIM {claim_id} borttagen: '{content}'")
        if opinion_count > 0:
            print(f"  ✓ {opinion_count} HAS_OPINION relationer borttagna")
        return True

  def edit_claim(self, claim_id, content=None, relation_type=None):
    """Redigera en CLAIM. Om content ändras uppdateras även embedding.
    
    Args:
        claim_id: claim_id för CLAIM-noden (t.ex. 'C1', 'C2')
        content: Nytt content (None = ingen ändring)
        relation_type: Ny type ('relation', None, eller '' för att ta bort)
    """
    with self.driver.session() as session:
        # Kontrollera att claimen finns
        check_query = "MATCH (c:CLAIM {claim_id: $claim_id}) RETURN c"
        result = session.run(check_query, claim_id=claim_id)
        if not result.single():
            print(f"\n✗ Ingen CLAIM hittades med ID {claim_id}")
            return False
        
        updates = []
        params = {"claim_id": claim_id}
        
        # Uppdatera content och embedding om content ändras
        if content is not None:
            embedding = self.create_embedding(content)
            updates.append("c.content = $content")
            updates.append("c.embedding = $embedding")
            params["content"] = content
            params["embedding"] = embedding
        
        # Uppdatera type
        if relation_type is not None:
            if relation_type == '':
                # Ta bort type property
                updates.append("c.type = null")
            else:
                updates.append("c.type = $type")
                params["type"] = relation_type
        
        if not updates:
            print(f"\n✗ Inga ändringar angivna")
            return False
        
        # Utför uppdateringen
        query = f"MATCH (c:CLAIM {{claim_id: $claim_id}}) SET {', '.join(updates)} RETURN c"
        session.run(query, **params)
        
        print(f"\n✓ CLAIM {claim_id} uppdaterad")
        if content is not None:
            print(f"  ✓ Nytt content: '{content}'")
            print(f"  ✓ Embedding uppdaterad")
        if relation_type is not None:
            if relation_type == '':
                print(f"  ✓ Type borttagen")
            else:
                print(f"  ✓ Ny type: {relation_type}")
        return True

  def create_opinion(self, npc_id, claim_id, belief_in, openness):
    """Skapa en HAS_OPINION relation mellan NPC och CLAIM med belief_in och openness attribut.
    
    Args:
        npc_id: ID för NPC-noden
        claim_id: claim_id för CLAIM-noden (t.ex. 'C1', 'C2')
        belief_in: Värde från -1 till 1 som indikerar tro på claimen
        openness: Värde från -1 till 1 som indikerar öppenhet att diskutera
    """
    with self.driver.session() as session:
        # Skapa HAS_OPINION relation med attribut
        query = """
        MATCH (npc:NPC {id: $npc_id})
        MATCH (c:CLAIM {claim_id: $claim_id})
        CREATE (npc)-[o:HAS_OPINION {belief_in: $belief_in, openness: $openness}]->(c)
        RETURN o
        """
        result = session.run(query, npc_id=npc_id, claim_id=claim_id, belief_in=belief_in, openness=openness)
        
        if result.single():
            print(f"\n✓ HAS_OPINION relation skapad: NPC '{npc_id}' -> CLAIM '{claim_id}' (belief: {belief_in}, openness: {openness})")
            return True
        else:
            print(f"\n✗ Kunde inte skapa HAS_OPINION. Kontrollera att NPC '{npc_id}' och CLAIM '{claim_id}' finns.")
            return False

