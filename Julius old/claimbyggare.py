from db_utils import (
    get_all_npcs, get_all_groups, get_all_claims, get_all_constants,
    select_from_menu, get_float_input, confirm_action,
    create_claim, create_knowledge, create_reference
)

TARGET_TYPES = ["CLAIM", "NPC", "GROUP", "OBJECT", "PLACE"]

def select_entities_with_knowledge(claim_id):
    """Låt användaren välja NPCs/grupper och ange BELIEF/STANCE för varje."""
    npcs = get_all_npcs()
    groups = get_all_groups()
    
    remaining_npcs = npcs.copy()
    remaining_groups = groups.copy()
    
    while True:
        # Skapa kombinerad lista med kvarvarande entiteter
        options = []
        entities = []
        
        for npc in remaining_npcs:
            options.append(f"[NPC] {npc}")
            entities.append({"name": npc, "type": "NPC"})
        
        for group in remaining_groups:
            options.append(f"[GROUP] {group}")
            entities.append({"name": group, "type": "GROUP"})
        
        options.append("--- KLAR ---")
        
        if len(options) == 1:  # Bara "KLAR" kvar
            print("\nAlla entiteter har valts!")
            break
        
        selected = select_from_menu("Välj vem som känner till denna claim:", options)
        
        if selected == "--- KLAR ---":
            break
        
        selected_index = options.index(selected)
        entity = entities[selected_index]
        
        print(f"\n=== Kunskap för {entity['name']} ({entity['type']}) ===")
        
        # Ange BELIEF
        print("\nBELIEF (intern övertygelse):")
        print("  -1 = tror inte alls, 0 = osäker, 1 = tror starkt")
        belief = get_float_input("Ange belief (-1.0 till 1.0): ", min_val=-1.0, max_val=1.0)
        
        # Ange STANCE
        print("\nSTANCE (yttre ställningstagande):")
        print("  -1 = motsätter sig öppet, 0 = neutral, 1 = förespråkar öppet")
        stance = get_float_input("Ange stance (-1.0 till 1.0): ", min_val=-1.0, max_val=1.0)
        
        # Skapa kunskapen
        create_knowledge(entity["name"], entity["type"], claim_id, belief, stance)
        
        # Ta bort från listorna
        if entity["type"] == "NPC":
            remaining_npcs.remove(entity["name"])
        else:
            remaining_groups.remove(entity["name"])

def add_references(claim_id):
    """Låt användaren lägga till referenser från claimen."""
    # Hämta alla listor (nollställda)
    claims = get_all_claims()
    npcs = get_all_npcs()
    groups = get_all_groups()
    constants = get_all_constants()
    
    # Håll koll på vad som redan refererats
    used_claims = set()
    used_npcs = set()
    used_groups = set()
    used_objects = set()
    used_places = set()
    
    while True:
        # Skapa lista med tillgängliga target-typer
        available_types = ["--- KLAR ---"]
        
        # Kolla vilka typer som har tillgängliga targets
        remaining_claims = [c for c in claims if c["id"] != claim_id and c["id"] not in used_claims]
        remaining_npcs = [n for n in npcs if n not in used_npcs]
        remaining_groups = [g for g in groups if g not in used_groups]
        remaining_objects = [c for c in constants if c["type"] == "OBJECT" and c["id"] not in used_objects]
        remaining_places = [c for c in constants if c["type"] == "PLACE" and c["id"] not in used_places]
        
        if remaining_claims:
            available_types.insert(0, "CLAIM")
        if remaining_npcs:
            available_types.insert(0, "NPC")
        if remaining_groups:
            available_types.insert(0, "GROUP")
        if remaining_objects:
            available_types.insert(0, "OBJECT")
        if remaining_places:
            available_types.insert(0, "PLACE")
        
        if len(available_types) == 1:  # Bara "KLAR" kvar
            print("\nAlla möjliga referenser har lagts till!")
            break
        
        target_type = select_from_menu("Välj typ av referens att lägga till:", available_types)
        
        if target_type == "--- KLAR ---":
            break
        
        if target_type == "CLAIM":
            options = [f"[{c['veracity']}] {c['content']}" for c in remaining_claims]
            selected_index = options.index(select_from_menu("Välj CLAIM:", options))
            target = remaining_claims[selected_index]
            create_reference(claim_id, target["id"], "CLAIM")
            used_claims.add(target["id"])
            
        elif target_type == "NPC":
            npc_name = select_from_menu("Välj NPC:", remaining_npcs)
            create_reference(claim_id, npc_name, "NPC")
            used_npcs.add(npc_name)
            
        elif target_type == "GROUP":
            group_name = select_from_menu("Välj GROUP:", remaining_groups)
            create_reference(claim_id, group_name, "GROUP")
            used_groups.add(group_name)
            
        elif target_type == "OBJECT":
            options = [c["name"] for c in remaining_objects]
            selected_name = select_from_menu("Välj OBJECT:", options)
            selected_index = options.index(selected_name)
            target = remaining_objects[selected_index]
            create_reference(claim_id, target["id"], "OBJECT")
            used_objects.add(target["id"])
            
        elif target_type == "PLACE":
            options = [c["name"] for c in remaining_places]
            selected_name = select_from_menu("Välj PLACE:", options)
            selected_index = options.index(selected_name)
            target = remaining_places[selected_index]
            create_reference(claim_id, target["id"], "PLACE")
            used_places.add(target["id"])

def main():
    print("=" * 50)
    print("         CLAIM BYGGARE")
    print("=" * 50)
    
    # Steg 1: Skapa claim content
    content = input("\nAnge claimens innehåll: ")
    
    # Steg 2: Välj veracity
    veracity = select_from_menu("Välj veracity:", ["truth", "lie"])
    
    # Steg 3: Fråga om relation type
    is_relation = confirm_action("Ska denna claim ha type='relation'?")
    relation_type = "relation" if is_relation else None
    
    # Skapa claimen och få tillbaka ID
    claim_id = create_claim(veracity, content, relation_type)
    
    if not claim_id:
        print("\n⚠ Kunde inte skapa claim")
        return
    
    # Steg 4: Lägg till kunskap (NPCs/grupper som känner till)
    print("\n" + "=" * 50)
    print("         STEG 2: KUNSKAP")
    print("=" * 50)
    print("Välj vilka NPCs och grupper som känner till denna claim.")
    
    select_entities_with_knowledge(claim_id)
    
    # Steg 5: Lägg till referenser
    print("\n" + "=" * 50)
    print("         STEG 3: REFERENSER")
    print("=" * 50)
    print("Lägg till referenser till andra noder.")
    
    add_references(claim_id)
    
    print("\n" + "=" * 50)
    print("         CLAIM SKAPAD!")
    print("=" * 50)
    print(f"Content: {content}")
    print(f"Veracity: {veracity}")
    if relation_type:
        print(f"Type: {relation_type}")

if __name__ == "__main__":
    main()
