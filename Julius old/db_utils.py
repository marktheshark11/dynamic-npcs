from neo4j import GraphDatabase
from langchain_community.embeddings import OllamaEmbeddings

# Database connection
driver = GraphDatabase.driver(
    "neo4j+s://7ab9efca.databases.neo4j.io", 
    auth=("neo4j", "9k6CKG5Mei8KtoVKtZqbre3EZBbuWRQ_SPzRkNGINpE")
)

# Embedding model
embed_model = OllamaEmbeddings(model="mxbai-embed-large")

# =============================================================================
# EMBEDDING FUNCTIONS
# =============================================================================

def create_embedding(text):
    """Skapa en embedding-vektor för ett dokument (claim content)."""
    # Inget prefix för dokument enligt mxbai-embed-large dokumentation
    return embed_model.embed_query(text)

def create_query_embedding(text):
    """Skapa en embedding-vektor för en sökfråga."""
    # Prefix för queries enligt mxbai-embed-large dokumentation
    return embed_model.embed_query(f"Represent this sentence for searching relevant passages: {text}")

def update_claim_embedding(claim_id):
    """Uppdatera embedding för en CLAIM baserat på dess content."""
    with driver.session() as session:
        # Hämta content
        result = session.run(
            "MATCH (c:CLAIM) WHERE id(c) = $claim_id RETURN c.content AS content",
            claim_id=claim_id
        )
        record = result.single()
        if not record:
            print(f"⚠ Ingen CLAIM hittades med ID {claim_id}")
            return False
        
        content = record["content"]
        embedding = create_embedding(content)
        
        # Uppdatera CLAIM med embedding
        session.run(
            "MATCH (c:CLAIM) WHERE id(c) = $claim_id SET c.embedding = $embedding",
            claim_id=claim_id, embedding=embedding
        )
        print(f"✓ Embedding uppdaterad för CLAIM: '{content[:50]}...'" if len(content) > 50 else f"✓ Embedding uppdaterad för CLAIM: '{content}'")
        return True

def update_all_claim_embeddings():
    """Uppdatera embeddings för alla CLAIM noder."""
    claims = get_all_claims()
    print(f"\nUppdaterar embeddings för {len(claims)} claims...")
    
    for claim in claims:
        update_claim_embedding(claim["id"])
    
    print(f"\n✓ Alla {len(claims)} embeddings uppdaterade!")

# =============================================================================
# RELATION DEFINITIONS
# =============================================================================

# STRUCTURAL: Sociala/familjerelationer (symmetriska eller med invers)
STRUCTURAL_RELATIONS = {
    "SIBLING_WITH": "SIBLING_WITH",      # Symmetrisk
    "FRIENDS_WITH": "FRIENDS_WITH",      # Symmetrisk
    "DATING": "DATING",                  # Symmetrisk
    "MARRIED_TO": "MARRIED_TO",          # Symmetrisk
    "DIVORCED_FROM": "DIVORCED_FROM",    # Symmetrisk
    "PARENT_TO": "CHILD_TO",             # Asymmetrisk
    "CHILD_TO": "PARENT_TO",             # Asymmetrisk
}

# AFFECTIVE: Känslomässiga kopplingar mellan NPCs (enkelriktade)
# Skapas alltid i par: AFFECTION (intern känsla) och DEMEANOUR (yttre uttryck)
# Värden: -1 (hatar/ogillande) till 1 (älskar/uppskattande)

# KNOWLEDGE: Kunskapskopplingar mellan NPC och FACT/LIE (via OPINION-nod)
# Skapas alltid i par: BELIEF (intern övertygelse) och STANCE (yttre ställningstagande)
# Värden: -1 (tror inte/motsätter sig) till 1 (tror starkt/förespråkar)

# Alla relationstyper för bakåtkompatibilitet
RELATION_TYPES = STRUCTURAL_RELATIONS

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def select_from_menu(prompt, options):
    """Visa en meny och låt användaren välja."""
    # print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        choice = input(f"Ange nummer (1-{len(options)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Ogiltigt val, försök igen.")

def confirm_action(message):
    """Fråga användaren om bekräftelse."""
    response = input(f"\n{message} (j/n): ")
    return response.lower() == 'j'

def get_float_input(prompt, min_val=0.0, max_val=1.0):
    """Hämta ett flyttal från användaren inom ett intervall."""
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                return value
            print(f"Värdet måste vara mellan {min_val} och {max_val}.")
        except ValueError:
            print("Ogiltigt värde, ange ett tal.")

# =============================================================================
# NPC FUNCTIONS
# =============================================================================

def get_all_npcs():
    """Hämta alla NPCs från databasen."""
    with driver.session() as session:
        result = session.run("MATCH (n:NPC) RETURN n.name AS name ORDER BY n.name")
        return [record["name"] for record in result]

def get_all_groups():
    """Hämta alla GROUP noder från databasen."""
    with driver.session() as session:
        result = session.run("MATCH (g:GROUP) RETURN g.name AS name ORDER BY g.name")
        return [record["name"] for record in result]

def create_npc(name):
    """Skapa en NPC med formaterat namn."""
    formatted_name = name.capitalize()
    
    with driver.session() as session:
        query = "MERGE (npc:NPC {name: $name})"
        session.run(query, name=formatted_name)
        print(f"\n✓ NPC '{formatted_name}' skapad")

def create_group(name):
    """Skapa en GROUP med formaterat namn."""
    formatted_name = name.capitalize()
    
    with driver.session() as session:
        query = "MERGE (g:GROUP {name: $name})"
        session.run(query, name=formatted_name)
        print(f"\n✓ GROUP '{formatted_name}' skapad")

def create_membership(npc_name, group_name):
    """Skapa en MEMBER_OF relation mellan NPC och GROUP."""
    with driver.session() as session:
        query = """
        MATCH (npc:NPC {name: $npc_name}), (g:GROUP {name: $group_name})
        MERGE (npc)-[r:MEMBER_OF]->(g)
        """
        session.run(query, npc_name=npc_name, group_name=group_name)
        print(f"\n✓ {npc_name} är nu MEMBER_OF {group_name}")

def create_claim(veracity, content, relation_type=None):
    """Skapa en CLAIM nod med given information, veracity, optional relation type och embedding."""
    
    # Skapa embedding för content
    embedding = create_embedding(content)

    with driver.session() as session:
        if relation_type:
            query = "CREATE (c:CLAIM {content: $content, veracity: $veracity, type: $relation_type, embedding: $embedding}) RETURN id(c) AS claim_id"
            result = session.run(query, content=content, veracity=veracity, relation_type=relation_type, embedding=embedding)
        else:
            query = "CREATE (c:CLAIM {content: $content, veracity: $veracity, embedding: $embedding}) RETURN id(c) AS claim_id"
            result = session.run(query, content=content, veracity=veracity, embedding=embedding)
        
        record = result.single()
        claim_id = record["claim_id"] if record else None
        print(f"\n✓ CLAIM skapad: '{content}' (veracity: {veracity})")
        return claim_id

def delete_claim(claim_id):
    """Ta bort en CLAIM nod och alla kopplade OPINION noder."""
    with driver.session() as session:
        # Hämta info om noden och räkna kopplade OPINION noder
        info_query = """
        MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
        OPTIONAL MATCH (opinion:OPINION)-[:ABOUT]->(claim)
        RETURN claim.veracity AS veracity, claim.content AS content, count(opinion) AS opinion_count
        """
        result = session.run(info_query, claim_id=claim_id)
        record = result.single()
        
        if not record or not record["content"]:
            print(f"\n⚠ Ingen CLAIM hittades med ID {claim_id}")
            return
        
        veracity = record["veracity"]
        content = record["content"]
        opinion_count = record["opinion_count"]
        
        # Ta bort OPINION noder och claim-noden
        delete_query = """
        MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
        OPTIONAL MATCH (opinion:OPINION)-[:ABOUT]->(claim)
        DETACH DELETE opinion, claim
        """
        session.run(delete_query, claim_id=claim_id)
        
        print(f"\n✓ CLAIM borttagen: '{content}' (veracity: {veracity})")
        if opinion_count > 0:
            print(f"✓ {opinion_count} kopplad(e) OPINION nod(er) borttagen(a)")

def delete_npc(name):
    """Ta bort en NPC och alla dess relationer."""
    with driver.session() as session:
        # Räkna relationer först
        count_query = """
        MATCH (n:NPC {name: $name})-[r]-()
        RETURN count(r) AS relation_count
        """
        result = session.run(count_query, name=name)
        record = result.single()
        relation_count = record["relation_count"] if record else 0
        
        # Ta bort NPC och alla relationer
        delete_query = """
        MATCH (n:NPC {name: $name})
        DETACH DELETE n
        """
        session.run(delete_query, name=name)
        
        print(f"\n✓ NPC '{name}' borttagen")
        if relation_count > 0:
            print(f"✓ {relation_count} relation(er) borttagna")

# =============================================================================
# RELATION FUNCTIONS
# =============================================================================

def create_structural_relation(name_1, name_2, relation_type, secrecy):
    """Skapa en STRUCTURAL relation mellan två NPCs (bidirektionell)."""
    inverse_type = STRUCTURAL_RELATIONS[relation_type]
    
    with driver.session() as session:
        # Skapa relationen från name_1 till name_2
        query = """
        MATCH (a:NPC {name: $name_1}), (b:NPC {name: $name_2})
        MERGE (a)-[r:%s]->(b)
        SET r.secrecy = $secrecy
        """ % relation_type
        session.run(query, name_1=name_1, name_2=name_2, secrecy=secrecy)
        
        # Skapa den omvända relationen från name_2 till name_1
        inverse_query = """
        MATCH (a:NPC {name: $name_1}), (b:NPC {name: $name_2})
        MERGE (b)-[r:%s]->(a)
        SET r.secrecy = $secrecy
        """ % inverse_type
        session.run(inverse_query, name_1=name_1, name_2=name_2, secrecy=secrecy)
        
        print(f"\n✓ {name_1} är {relation_type.replace('_', ' ').lower()} {name_2}")
        print(f"✓ {name_2} är {inverse_type.replace('_', ' ').lower()} {name_1}")
        print(f"  (secrecy: {secrecy})")

def create_affective_relation(name_1, name_2, affection, demeanour):
    """
    Skapa en AFFECTIVE koppling mellan två NPCs.
    Skapar alltid två relationer:
    - AFFECTION: Intern känsla (-1 hatar till 1 älskar)
    - DEMEANOUR: Yttre uttryck (-1 ogillande till 1 uppskattande)
    """
    with driver.session() as session:
        query = """
        MATCH (a:NPC {name: $name_1}), (b:NPC {name: $name_2})
        MERGE (a)-[aff:AFFECTION]->(b)
        SET aff.intensity = $affection
        MERGE (a)-[dem:DEMEANOUR]->(b)
        SET dem.intensity = $demeanour
        """
        session.run(query, name_1=name_1, name_2=name_2, affection=affection, demeanour=demeanour)
        
        print(f"\n✓ {name_1} → {name_2}")
        print(f"  AFFECTION: {affection} (intern känsla)")
        print(f"  DEMEANOUR: {demeanour} (yttre uttryck)")

def create_relation(name_1, name_2, relation_type):
    """Bakåtkompatibel funktion - skapar STRUCTURAL relation utan secrecy."""
    create_structural_relation(name_1, name_2, relation_type, secrecy=0)

def remove_relations(name_1, name_2):
    """Ta bort alla relationer mellan två NPCs (båda riktningarna)."""
    with driver.session() as session:
        query = """
        MATCH (a:NPC {name: $name_1})-[r]-(b:NPC {name: $name_2})
        DELETE r
        RETURN count(r) AS deleted_count
        """
        result = session.run(query, name_1=name_1, name_2=name_2)
        record = result.single()
        deleted_count = record["deleted_count"] if record else 0
        
        if deleted_count > 0:
            print(f"\n✓ Tog bort {deleted_count} relation(er) mellan {name_1} och {name_2}")
        else:
            print(f"\n⚠ Inga relationer hittades mellan {name_1} och {name_2}")

# =============================================================================
# CONSTANT FUNCTIONS (OBJECT, PLACE)
# =============================================================================

def create_object(name):
    """Skapa en OBJECT nod med name-property."""
    formatted_name = name.capitalize()
    
    with driver.session() as session:
        query = "MERGE (o:OBJECT {name: $name})"
        session.run(query, name=formatted_name)
        print(f"\n✓ OBJECT '{formatted_name}' skapad")

def create_place(name):
    """Skapa en PLACE nod med name-property."""
    formatted_name = name.capitalize()
    
    with driver.session() as session:
        query = "MERGE (p:PLACE {name: $name})"
        session.run(query, name=formatted_name)
        print(f"\n✓ PLACE '{formatted_name}' skapad")

def get_all_constants():
    """Hämta alla OBJECT och PLACE noder från databasen."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c) WHERE c:OBJECT OR c:PLACE
            RETURN labels(c)[0] AS type, c.name AS name, id(c) AS id
            ORDER BY labels(c)[0], c.name
        """)
        return [{"type": record["type"], "name": record["name"], "id": record["id"]} 
                for record in result]

def create_reference(claim_id, target, target_type):
    """
    Skapa en REFERENCE relation mellan CLAIM och CLAIM/NPC/OBJECT/PLACE.
    target: id för CLAIM/OBJECT/PLACE, eller namn för NPC
    target_type: "CLAIM", "NPC", "OBJECT", eller "PLACE"
    """
    with driver.session() as session:
        if target_type == "CLAIM":
            query = """
            MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
            MATCH (target:CLAIM) WHERE id(target) = $target_id
            MERGE (claim)-[r:REFERENCE]->(target)
            RETURN claim.content AS claim_content, target.content AS target_content, target.veracity AS target_veracity
            """
            result = session.run(query, claim_id=claim_id, target_id=target)
            record = result.single()
            
            if record:
                print(f"\n✓ CLAIM \"{record['claim_content']}\"")
                print(f"  REFERENCE →")
                print(f"  [CLAIM:{record['target_veracity']}] \"{record['target_content']}\"")
            else:
                print("\n⚠ Kunde inte skapa referensen")
                
        elif target_type == "NPC":
            query = """
            MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
            MATCH (npc:NPC {name: $npc_name})
            MERGE (claim)-[r:REFERENCE]->(npc)
            RETURN claim.content AS claim_content, npc.name AS npc_name
            """
            result = session.run(query, claim_id=claim_id, npc_name=target)
            record = result.single()
            
            if record:
                print(f"\n✓ CLAIM \"{record['claim_content']}\"")
                print(f"  REFERENCE →")
                print(f"  [NPC] {record['npc_name']}")
            else:
                print("\n⚠ Kunde inte skapa referensen")
                
        else:  # OBJECT eller PLACE
            query = """
            MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
            MATCH (target) WHERE id(target) = $target_id
            MERGE (claim)-[r:REFERENCE]->(target)
            RETURN claim.content AS claim_content, labels(target)[0] AS target_type, target.name AS target_name
            """
            result = session.run(query, claim_id=claim_id, target_id=target)
            record = result.single()
            
            if record:
                print(f"\n✓ CLAIM \"{record['claim_content']}\"")
                print(f"  REFERENCE →")
                print(f"  [{record['target_type']}] {record['target_name']}")
            else:
                print("\n⚠ Kunde inte skapa referensen")

# =============================================================================
# KNOWLEDGE FUNCTIONS
# =============================================================================

def get_all_claims():
    """Hämta alla CLAIM noder från databasen."""
    with driver.session() as session:
        result = session.run("""
            MATCH (c:CLAIM)
            RETURN c.veracity AS veracity, c.content AS content, id(c) AS id
            ORDER BY c.veracity, c.content
        """)
        return [{"veracity": record["veracity"], "content": record["content"], "id": record["id"]} 
                for record in result]

def create_knowledge(entity_name, entity_type, claim_id, belief, stance):
    """
    Skapa en kunskap-koppling mellan NPC/GROUP och CLAIM.
    Strukturen: (NPC/GROUP)-[BELIEF {intensity}]->(CLAIM)
                (NPC/GROUP)-[STANCE {intensity}]->(CLAIM)
    
    entity_type: "NPC" eller "GROUP"
    
    Skapar alltid två relationer direkt till CLAIM:
    - BELIEF: Intern övertygelse (-1 tror inte till 1 tror starkt)
    - STANCE: Yttre ställningstagande (-1 motsätter sig till 1 förespråkar)
    """
    with driver.session() as session:
        query = """
        MATCH (entity:%s {name: $entity_name})
        MATCH (claim:CLAIM) WHERE id(claim) = $claim_id
        MERGE (entity)-[b:BELIEF]->(claim)
        SET b.intensity = $belief
        MERGE (entity)-[s:STANCE]->(claim)
        SET s.intensity = $stance
        RETURN claim.content AS content, claim.veracity AS veracity
        """ % entity_type
        
        result = session.run(query, entity_name=entity_name, claim_id=claim_id, belief=belief, stance=stance)
        record = result.single()
        
        if record:
            content = record["content"]
            veracity = record["veracity"]
            print(f"\n✓ {entity_name} ({entity_type}) → [{veracity}] \"{content}\"")
            print(f"  BELIEF: {belief} (intern övertygelse)")
            print(f"  STANCE: {stance} (yttre ställningstagande)")

def get_entity_knowledge(entity_name, entity_type):
    """Hämta alla kunskaps-kopplingar för en NPC eller GROUP."""
    with driver.session() as session:
        query = """
        MATCH (entity:%s {name: $entity_name})-[b:BELIEF]->(claim:CLAIM)
        OPTIONAL MATCH (entity)-[s:STANCE]->(claim)
        RETURN id(claim) AS claim_id, claim.veracity AS veracity, claim.content AS content,
               b.intensity AS belief, s.intensity AS stance
        ORDER BY claim.veracity, claim.content
        """ % entity_type
        result = session.run(query, entity_name=entity_name)
        return [{"claim_id": record["claim_id"], "veracity": record["veracity"], 
                 "content": record["content"], "belief": record["belief"], 
                 "stance": record["stance"]} for record in result]

def delete_knowledge(entity_name, entity_type, claim_id):
    """Ta bort BELIEF och STANCE relationer mellan entity och claim."""
    with driver.session() as session:
        # Hämta info om kopplingen först
        info_query = """
        MATCH (entity:%s {name: $entity_name})-[:BELIEF]->(claim:CLAIM)
        WHERE id(claim) = $claim_id
        RETURN claim.veracity AS veracity, claim.content AS content
        """ % entity_type
        result = session.run(info_query, entity_name=entity_name, claim_id=claim_id)
        record = result.single()
        
        if not record:
            print(f"\n⚠ Ingen kunskap hittades")
            return
        
        veracity = record["veracity"]
        content = record["content"]
        
        # Ta bort BELIEF och STANCE relationerna
        delete_query = """
        MATCH (entity:%s {name: $entity_name})-[b:BELIEF]->(claim:CLAIM)
        WHERE id(claim) = $claim_id
        OPTIONAL MATCH (entity)-[s:STANCE]->(claim)
        DELETE b, s
        """ % entity_type
        session.run(delete_query, entity_name=entity_name, claim_id=claim_id)
        
        print(f"\n✓ Tog bort {entity_name}s kunskap om [{veracity}] \"{content}\"")

# =============================================================================
# LOGIC FUNCTIONS
# =============================================================================

def create_logic_relation(from_info_id, to_info_id):
    """
    Skapa en BASED_ON relation mellan två CLAIM noder.
    Strukturen: (CLAIM)-[BASED_ON]->(CLAIM)
    """
    with driver.session() as session:
        query = """
        MATCH (from_claim:CLAIM) WHERE id(from_claim) = $from_id
        MATCH (to_claim:CLAIM) WHERE id(to_claim) = $to_id
        MERGE (from_claim)-[r:BASED_ON]->(to_claim)
        RETURN from_claim.veracity AS from_veracity, from_claim.content AS from_content,
               to_claim.veracity AS to_veracity, to_claim.content AS to_content
        """
        
        result = session.run(query, from_id=from_info_id, to_id=to_info_id)
        record = result.single()
        
        if record:
            print(f"\n✓ [{record['from_veracity']}] \"{record['from_content']}\"")
            print(f"  BASED_ON →")
            print(f"  [{record['to_veracity']}] \"{record['to_content']}\"")
        else:
            print("\n⚠ Kunde inte skapa relationen")
