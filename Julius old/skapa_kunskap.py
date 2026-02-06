from db_utils import (
    get_all_npcs, get_all_groups, get_all_claims,
    select_from_menu, get_float_input,
    create_knowledge
)

def format_claim_options(claims):
    """Formatera claims för visning i menyn."""
    return [f"[{c['veracity']}] {c['content']}" for c in claims]

def select_entity():
    """Låt användaren välja en NPC eller GROUP."""
    npcs = get_all_npcs()
    groups = get_all_groups()
    
    if not npcs and not groups:
        print("Det finns inga NPCs eller grupper i databasen.")
        return None, None
    
    # Skapa kombinerad lista
    options = []
    entities = []
    
    for npc in npcs:
        options.append(f"[NPC] {npc}")
        entities.append({"name": npc, "type": "NPC"})
    
    for group in groups:
        options.append(f"[GROUP] {group}")
        entities.append({"name": group, "type": "GROUP"})
    
    selected = select_from_menu("Välj NPC eller GROUP:", options)
    selected_index = options.index(selected)
    entity = entities[selected_index]
    
    return entity["name"], entity["type"]

def main():
    # Välj entitet (NPC eller GROUP)
    entity_name, entity_type = select_entity()
    if not entity_name:
        return
    
    # Hämta alla CLAIM
    claims = get_all_claims()
    
    if not claims:
        print("Det finns inga CLAIM i databasen.")
        return
    
    print(f"\n=== Skapar kunskap för: {entity_name} ({entity_type}) ===")
    
    # Välj CLAIM
    claim_options = format_claim_options(claims)
    selected_index = claim_options.index(select_from_menu("Välj CLAIM:", claim_options))
    selected_claim = claims[selected_index]
    
    # Ange BELIEF (intern övertygelse)
    print("\nBELIEF (intern övertygelse):")
    print("  -1 = tror inte alls, 0 = osäker, 1 = tror starkt")
    belief = get_float_input("Ange belief (-1.0 till 1.0): ", min_val=-1.0, max_val=1.0)
    
    # Ange STANCE (yttre ställningstagande)
    print("\nSTANCE (yttre ställningstagande):")
    print("  -1 = motsätter sig öppet, 0 = neutral, 1 = förespråkar öppet")
    stance = get_float_input("Ange stance (-1.0 till 1.0): ", min_val=-1.0, max_val=1.0)
    
    # Skapa kunskapen
    create_knowledge(entity_name, entity_type, selected_claim["id"], belief, stance)

if __name__ == "__main__":
    main()
