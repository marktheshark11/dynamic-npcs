import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_community.embeddings import OllamaEmbeddings

# Setup
load_dotenv()
db_user = os.getenv("NEO4J_USER")
db_password = os.getenv("NEO4J_PASSWORD")
db_uri = os.getenv('NEO4J_URI')

if (db_uri):
  driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))
embed_model = OllamaEmbeddings(model="mxbai-embed-large")

# Helper functions
def create_query_embedding(text):
    """Skapa en embedding-vektor för en sökfråga."""
    return embed_model.embed_query(f"Represent this sentence for searching relevant passages: {text}")

def select_from_menu(prompt, options):
    """Visa en meny och låt användaren välja."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    
    while True:
        choice = input(f"Ange nummer (1-{len(options)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Ogiltigt val, försök igen.")

def get_all_npcs():
    """Hämta alla NPC-namn från databasen."""
    with driver.session() as session:
        result = session.run("MATCH (n:NPC) RETURN n.name AS name ORDER BY n.name")
        return [record["name"] for record in result]

# =============================================================================
# RENDERING: Modifiera claim-text baserat på HAS_OPINION (belief_in/openness)
# =============================================================================

def render_claim(content, belief_in, openness):
    """
    Rendera en claim baserat på HAS_OPINION relation (belief_in och openness).
    
    belief_in:
      - |värde| 0.7-1.0 → ingen modifiering
      - |värde| 0.3-0.6 → prefix "Det är möjligt att "
      - |värde| 0.0-0.2 → prefix "Det är oklart ifall "
    
    openness (samma tecken som belief_in):
      - |värde| 0.7-1.0 → suffix "vilket du är bekväm att prata om"
      - |värde| 0.3-0.6 → ingen modifiering
      - |värde| 0.0-0.2 → suffix "vilket du undviker att prata om"
    
    openness (motsatt tecken som belief_in):
      - |värde| 0.7-1.0 → suffix "men det är du öppen med att neka"
      - |värde| 0.3-0.6 → suffix "men det nekar du"
      - |värde| 0.0-0.2 → suffix "vilket du undviker att prata om"
    """
    text = content
    
    # Hantera None-värden
    b_value = abs(belief_in) if belief_in is not None else 1.0
    o_value = abs(openness) if openness is not None else 0.5
    
    # Kolla om belief_in och openness har motsatt tecken
    opposite_signs = False
    if belief_in is not None and openness is not None:
        opposite_signs = (belief_in >= 0) != (openness >= 0)
    
    # Lägg till prefix baserat på belief_in
    if b_value <= 0.2:
        text = f"Det är oklart ifall {text[0].lower()}{text[1:]}"
    elif b_value <= 0.6:
        text = f"Det är möjligt att {text[0].lower()}{text[1:]}"
    # else: 0.7-1.0, ingen modifiering
    
    # Ta bort punkt om den finns i slutet
    text = text.rstrip('.')
    
    # Lägg till suffix baserat på openness
    if opposite_signs:
        # belief_in och openness har motsatt tecken
        if o_value >= 0.7:
            text = f"{text}, men det är du öppen med att neka."
        elif o_value >= 0.3:
            text = f"{text}, men det nekar du."
        else:
            text = f"{text}, vilket du undviker att prata om."
    else:
        # belief_in och openness har samma tecken (eller openness saknas)
        if o_value >= 0.7:
            text = f"{text}, vilket du är bekväm att prata om."
        elif o_value <= 0.2:
            text = f"{text}, vilket du undviker att prata om."
        else:
            text = f"{text}."
    
    return text

# =============================================================================
# STEG 1: Hitta top claims via semantisk sökning
# =============================================================================

def get_accessible_claim_ids(npc_name):
    """Hämta alla claim-IDs som NPC:n har tillgång till via HAS_OPINION."""
    with driver.session() as session:
        result = session.run("""
            MATCH (n:NPC {name: $npc_name})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:HAS_OPINION]->(c2:CLAIM)
            WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
            UNWIND claims AS c
            WITH c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
            RETURN DISTINCT elementId(c) AS id
        """, npc_name=npc_name)
        return [r["id"] for r in result]

def find_top_claims(npc_name, query, top_k=5):
    """Semantisk sökning: hitta de mest relevanta claims för frågan."""
    accessible_ids = get_accessible_claim_ids(npc_name)
    if not accessible_ids:
        return []
    
    query_embedding = create_query_embedding(query)
    
    with driver.session() as session:
        result = session.run("""
            CALL db.index.vector.queryNodes('claim_index', $top_k * 3, $query_vector)
            YIELD node, score
            WHERE elementId(node) IN $accessible_ids
            RETURN elementId(node) AS id, 
                   node.content AS content, 
                   node.type AS type,
                   score
            LIMIT $top_k
        """, query_vector=query_embedding, accessible_ids=accessible_ids, top_k=top_k)
        
        return [{
            "id": r["id"], 
            "content": r["content"], 
            "type": r["type"],  # None eller "relation"
            "score": r["score"]
        } for r in result]

# =============================================================================
# STEG 2: Hitta refererade konstanter och relation-claims
# =============================================================================

def get_constants_from_claims(claim_ids):
    """Hämta alla konstanter (NPC, PLACE, OBJECT) som refereras av claims."""
    if not claim_ids:
        return []
    
    with driver.session() as session:
        result = session.run("""
            MATCH (c:CLAIM) WHERE elementId(c) IN $claim_ids
            MATCH (c)-[:REFERENCE]->(target)
            WHERE target:NPC OR target:PLACE OR target:OBJECT
            RETURN DISTINCT labels(target)[0] AS type, target.name AS name, elementId(target) AS id
        """, claim_ids=claim_ids)
        return [{"type": r["type"], "name": r["name"], "id": r["id"]} for r in result]

def find_relation_claims(npc_name, constant_ids, min_refs=2):
    """
    Hitta relation-claims som refererar till minst min_refs konstanter.
    Returnerar endast claims med type='relation'.
    """
    if not constant_ids or len(constant_ids) < min_refs:
        return []
    
    with driver.session() as session:
        result = session.run("""
            MATCH (n:NPC {name: $npc_name})
            OPTIONAL MATCH (n)-[:HAS_OPINION]->(c1:CLAIM {type: "relation"})
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:HAS_OPINION]->(c2:CLAIM {type: "relation"})
            WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
            UNWIND claims AS c
            WITH c WHERE c IS NOT NULL
            
            // Räkna hur många av våra konstanter denna claim refererar till
            MATCH (c)-[:REFERENCE]->(target)
            WHERE elementId(target) IN $constant_ids
            WITH c, count(DISTINCT target) AS ref_count
            WHERE ref_count >= $min_refs
            
            RETURN elementId(c) AS id, 
                   c.content AS content, 
                   c.type AS type,
                   ref_count
        """, npc_name=npc_name, constant_ids=constant_ids, min_refs=min_refs)
        
        return [{
            "id": r["id"],
            "content": r["content"],
            "type": r["type"],
            "score": 0.0  # Ingen semantisk score för dessa
        } for r in result]

# =============================================================================
# STEG 3: Ta bort dubbletter
# =============================================================================

def remove_duplicates(claims):
    """Ta bort dubbletter baserat på claim ID."""
    seen = set()
    unique = []
    for claim in claims:
        if claim["id"] not in seen:
            seen.add(claim["id"])
            unique.append(claim)
    return unique

# =============================================================================
# STEG 4: Gruppera claims i referenskedjor
# =============================================================================

def get_reference_chain(claim_id, npc_name):
    """
    Hämta referenskedjan för en claim (djupaste först).
    Inkluderar HAS_OPINION belief_in och openness värden för rendering.
    """
    with driver.session() as session:
        result = session.run("""
            MATCH path = (start:CLAIM)-[:REFERENCE*0..5]->(ref:CLAIM)
            WHERE elementId(start) = $claim_id
            WITH ref, length(path) AS depth
            ORDER BY depth DESC
            
            // Hämta HAS_OPINION från NPC eller via GROUP
            OPTIONAL MATCH (n:NPC {name: $npc_name})-[o:HAS_OPINION]->(ref)
            OPTIONAL MATCH (n:NPC {name: $npc_name})-[:MEMBER_OF]->(g:GROUP)-[go:HAS_OPINION]->(ref)
            
            WITH ref, depth,
                 COALESCE(o.belief_in, go.belief_in) AS belief_in,
                 COALESCE(o.openness, go.openness) AS openness
            
            RETURN DISTINCT elementId(ref) AS id, 
                   ref.content AS content, 
                   ref.type AS type, 
                   depth,
                   belief_in,
                   openness
        """, claim_id=claim_id, npc_name=npc_name)
        
        return [{
            "id": r["id"], 
            "content": r["content"], 
            "type": r["type"], 
            "depth": r["depth"],
            "belief_in": r["belief_in"],
            "openness": r["openness"]
        } for r in result]

def build_claim_chains(claims, npc_name):
    """
    Gruppera claims i kedjor baserat på referens-relationer.
    Renderar varje claim individuellt baserat på HAS_OPINION (belief_in/openness).
    """
    if not claims:
        return []
    
    claim_ids = {c["id"] for c in claims}
    claims_in_others_chain = set()
    
    # Identifiera vilka claims som ingår i andras kedjor
    for claim in claims:
        chain = get_reference_chain(claim["id"], npc_name)
        for c in chain:
            if c["id"] != claim["id"] and c["id"] in claim_ids:
                claims_in_others_chain.add(c["id"])
    
    # Bygg kedjor
    processed = set()
    chain_metadata = []
    
    for claim in claims:
        if claim["id"] in claims_in_others_chain or claim["id"] in processed:
            continue
        
        chain = get_reference_chain(claim["id"], npc_name)
        chain = [c for c in chain if c["id"] not in processed]
        
        if not chain:
            continue
        
        for c in chain:
            processed.add(c["id"])
        
        # Rendera varje claim individuellt och kombinera
        rendered_parts = []
        for c in chain:
            rendered = render_claim(
                c["content"],
                c["belief_in"],
                c["openness"]
            )
            rendered_parts.append(rendered)
        
        combined = " ".join(rendered_parts)
        
        # Kolla om kedjan innehåller relation-claims
        has_relation = any(c["type"] == "relation" for c in chain)
        
        chain_metadata.append({
            "content": combined,
            "is_relation": has_relation,
            "chain_length": len(chain)
        })
    
    return chain_metadata

# =============================================================================
# STEG 5 & 6: Separera och formatera output
# =============================================================================

def build_prompt(npc_name, chain_metadata, question):
    """Bygg prompt med non-relation claims först, sedan relation claims."""
    
    non_relation = [c for c in chain_metadata if not c["is_relation"]]
    relation = [c for c in chain_metadata if c["is_relation"]]
    
    prompt = f"SYSTEM: Du är {npc_name}. Svara kortfattat och håll dig till din karaktär.\n\n"
    
    # Non-relation claims
    prompt += "DIN KUNSKAP OM FRÅGAN:\n"
    if non_relation:
        for c in non_relation:
            prompt += f"- {c['content']}\n"
    else:
        prompt += "- (Ingen relevant kunskap)\n"
    
    # Relation claims
    prompt += "\nDINA RELATIONER:\n"
    if relation:
        for c in relation:
            prompt += f"- {c['content']}\n"
    else:
        prompt += "- (Inga relevanta relationer)\n"
    
    prompt += f"\nFRÅGA: {question}\n{npc_name.upper()}:"
    
    return prompt

# =============================================================================
# HUVUDPROGRAM
# =============================================================================

def main():
    print("=" * 50)
    print("         HITTA INFO")
    print("=" * 50)
    
    # Välj NPC
    npcs = get_all_npcs()
    if not npcs:
        print("\n⚠ Inga NPCs hittades")
        return
    
    npc_name = select_from_menu("Välj karaktär:", npcs)
    question = input("\nSkriv din fråga: ")
    
    print("\n" + "-" * 50)
    
    # STEG 1: Semantisk sökning
    print("Steg 1: Söker efter relevanta claims...")
    top_claims = find_top_claims(npc_name, question, top_k=3)
    
    if not top_claims:
        print("⚠ Inga claims hittades")
        return
    
    print(f"  → Hittade {len(top_claims)} grund-claims:")
    print("-" * 40)
    for i, c in enumerate(top_claims, 1):
        tag = "[REL]" if c["type"] == "relation" else "[INF]"
        print(f"  {i}. {tag} (id:{c['id']}, score:{c['score']:.3f})")
        print(f"     {c['content']}")
    print("-" * 40)
    
    # STEG 2: Hitta konstanter och relation-claims
    print("\nSteg 2: Söker efter relation-claims...")
    claim_ids = [c["id"] for c in top_claims]
    constants = get_constants_from_claims(claim_ids)
    constant_ids = [c["id"] for c in constants]
    
    print(f"  → Konstanter: {', '.join(c['name'] for c in constants) if constants else 'inga'}")
    
    relation_claims = find_relation_claims(npc_name, constant_ids, min_refs=2)
    print(f"  → Hittade {len(relation_claims)} relation-claims:")
    if relation_claims:
        print("-" * 40)
        for i, c in enumerate(relation_claims, 1):
            print(f"  {i}. (id:{c['id']}, refs:{c.get('ref_count', '?')})")
            print(f"     {c['content']}")
        print("-" * 40)
    
    # STEG 3: Kombinera och ta bort dubbletter
    print("\nSteg 3: Tar bort dubbletter...")
    all_claims = top_claims + relation_claims
    unique_claims = remove_duplicates(all_claims)
    print(f"  → {len(unique_claims)} unika claims")
    
    # STEG 4: Gruppera i kedjor och rendera
    print("\nSteg 4: Grupperar i referenskedjor och renderar...")
    chain_metadata = build_claim_chains(unique_claims, npc_name)
    print(f"  → {len(chain_metadata)} kedjor genererade")
    
    # STEG 5 & 6: Separera och visa
    non_rel = [c for c in chain_metadata if not c["is_relation"]]
    rel = [c for c in chain_metadata if c["is_relation"]]
    
    print(f"\nSteg 5: Non-relation claims ({len(non_rel)} st):")
    for c in non_rel:
        chain_tag = f" [kedja: {c['chain_length']}]" if c["chain_length"] > 1 else ""
        print(f"  - {c['content'][:70]}...{chain_tag}")
    
    print(f"\nSteg 6: Relation claims ({len(rel)} st):")
    for c in rel:
        chain_tag = f" [kedja: {c['chain_length']}]" if c["chain_length"] > 1 else ""
        print(f"  - {c['content'][:70]}...{chain_tag}")
    
    # Bygg och visa prompt
    prompt = build_prompt(npc_name, chain_metadata, question)
    
    print("\n" + "=" * 50)
    print("GENERERAD PROMPT:")
    print("=" * 50)
    print(prompt)
    
    driver.close()

def get_prompt_test():
  print("=" * 50)
  print("         HITTA INFO")
  print("=" * 50)
  
  # Välj NPC
  npcs = get_all_npcs()
  if not npcs:
      print("\n⚠ Inga NPCs hittades")
      return
  
  npc_name = select_from_menu("Välj karaktär:", npcs)
  question = input("\nSkriv din fråga: ")
  
  print("\n" + "-" * 50)
  
  # STEG 1: Semantisk sökning
  print("Steg 1: Söker efter relevanta claims...")
  top_claims = find_top_claims(npc_name, question, top_k=3)
  
  if not top_claims:
      print("⚠ Inga claims hittades")
      return
  
  print(f"  → Hittade {len(top_claims)} grund-claims:")
  print("-" * 40)
  for i, c in enumerate(top_claims, 1):
      tag = "[REL]" if c["type"] == "relation" else "[INF]"
      print(f"  {i}. {tag} (id:{c['id']}, score:{c['score']:.3f})")
      print(f"     {c['content']}")
  print("-" * 40)
  
  # STEG 2: Hitta konstanter och relation-claims
  print("\nSteg 2: Söker efter relation-claims...")
  claim_ids = [c["id"] for c in top_claims]
  constants = get_constants_from_claims(claim_ids)
  constant_ids = [c["id"] for c in constants]
  
  print(f"  → Konstanter: {', '.join(c['name'] for c in constants) if constants else 'inga'}")
  
  relation_claims = find_relation_claims(npc_name, constant_ids, min_refs=2)
  print(f"  → Hittade {len(relation_claims)} relation-claims:")
  if relation_claims:
      print("-" * 40)
      for i, c in enumerate(relation_claims, 1):
          print(f"  {i}. (id:{c['id']}, refs:{c.get('ref_count', '?')})")
          print(f"     {c['content']}")
      print("-" * 40)
  
  # STEG 3: Kombinera och ta bort dubbletter
  print("\nSteg 3: Tar bort dubbletter...")
  all_claims = top_claims + relation_claims
  unique_claims = remove_duplicates(all_claims)
  print(f"  → {len(unique_claims)} unika claims")
  
  # STEG 4: Gruppera i kedjor och rendera
  print("\nSteg 4: Grupperar i referenskedjor och renderar...")
  chain_metadata = build_claim_chains(unique_claims, npc_name)
  print(f"  → {len(chain_metadata)} kedjor genererade")
  
  # STEG 5 & 6: Separera och visa
  non_rel = [c for c in chain_metadata if not c["is_relation"]]
  rel = [c for c in chain_metadata if c["is_relation"]]
  
  print(f"\nSteg 5: Non-relation claims ({len(non_rel)} st):")
  for c in non_rel:
      chain_tag = f" [kedja: {c['chain_length']}]" if c["chain_length"] > 1 else ""
      print(f"  - {c['content'][:70]}...{chain_tag}")
  
  print(f"\nSteg 6: Relation claims ({len(rel)} st):")
  for c in rel:
      chain_tag = f" [kedja: {c['chain_length']}]" if c["chain_length"] > 1 else ""
      print(f"  - {c['content'][:70]}...{chain_tag}")
  
  # Bygg och visa prompt
  prompt = build_prompt(npc_name, chain_metadata, question)
  return prompt  

if __name__ == "__main__":
    main()
