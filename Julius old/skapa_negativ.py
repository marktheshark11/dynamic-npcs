from db_utils import driver, get_all_npcs, select_from_menu

def get_claims_for_npc(npc_name):
    """Hämta alla claims som en NPC har tillgång till."""
    with driver.session() as session:
        result = session.run("""
            MATCH (n:NPC {name: $npc_name})
            OPTIONAL MATCH (n)-[:BELIEF]->(c1:CLAIM)
            OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:BELIEF]->(c2:CLAIM)
            WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS claims
            UNWIND claims AS c
            WITH c WHERE c IS NOT NULL
            RETURN id(c) AS id, 
                   c.content AS content, 
                   c.negative AS negative,
                   c.type AS type
            ORDER BY c.content
        """, npc_name=npc_name)
        return [{"id": r["id"], "content": r["content"], "negative": r["negative"], "type": r["type"]} 
                for r in result]

def set_negative(claim_id, negative_text):
    """Sätt negative-property på en claim."""
    with driver.session() as session:
        session.run("""
            MATCH (c:CLAIM) WHERE id(c) = $claim_id
            SET c.negative = $negative_text
        """, claim_id=claim_id, negative_text=negative_text)

def remove_negative(claim_id):
    """Ta bort negative-property från en claim."""
    with driver.session() as session:
        session.run("""
            MATCH (c:CLAIM) WHERE id(c) = $claim_id
            REMOVE c.negative
        """, claim_id=claim_id)

def main():
    print("=" * 50)
    print("     SKAPA/REDIGERA NEGATIV")
    print("=" * 50)
    
    # Välj NPC för att se claims
    npcs = get_all_npcs()
    if not npcs:
        print("\n⚠ Inga NPCs hittades")
        return
    
    npc_name = select_from_menu("Välj karaktär:", npcs)
    
    # Hämta claims
    claims = get_claims_for_npc(npc_name)
    if not claims:
        print("\n⚠ Inga claims hittades för denna NPC")
        return
    
    # Visa claims
    print(f"\nClaims för {npc_name}:")
    print("-" * 50)
    for i, claim in enumerate(claims, 1):
        type_tag = "[REL]" if claim["type"] == "relation" else "[INF]"
        neg_status = "✓" if claim["negative"] else "✗"
        print(f"  {i}. {type_tag} [neg:{neg_status}] {claim['content'][:50]}...")
    
    # Välj claim
    try:
        choice = int(input("\nVälj claim att redigera (nummer): "))
        if choice < 1 or choice > len(claims):
            print("⚠ Ogiltigt val")
            return
    except ValueError:
        print("⚠ Ange ett nummer")
        return
    
    selected = claims[choice - 1]
    
    print(f"\nVald claim:")
    print(f"  Content:  {selected['content']}")
    print(f"  Negative: {selected['negative'] or '(ej satt)'}")
    
    # Meny
    print("\nVad vill du göra?")
    print("  1. Sätt/uppdatera negative")
    print("  2. Ta bort negative")
    print("  3. Avbryt")
    
    action = input("\nVälj (1-3): ")
    
    if action == "1":
        print("\nSkriv negativet (motsatsen till claimets innehåll):")
        negative_text = input("> ")
        if negative_text.strip():
            set_negative(selected["id"], negative_text.strip())
            print(f"\n✓ Negative satt: '{negative_text.strip()}'")
        else:
            print("⚠ Tomt värde, avbryter")
    
    elif action == "2":
        if selected["negative"]:
            remove_negative(selected["id"])
            print("\n✓ Negative borttaget")
        else:
            print("⚠ Denna claim har inget negative att ta bort")
    
    else:
        print("Avbryter")

if __name__ == "__main__":
    main()
