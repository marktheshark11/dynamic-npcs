from db_utils import (
    get_all_claims, get_all_constants, get_all_npcs, 
    select_from_menu, create_reference
)

TARGET_TYPES = ["CLAIM", "NPC", "OBJECT", "PLACE"]

def format_claim_options(claims):
    """Formatera claims för visning i menyn."""
    return [f"[{c['veracity']}] {c['content']}" for c in claims]

def main():
    # Hämta alla claims
    claims = get_all_claims()
    
    if not claims:
        print("Det finns inga CLAIM i databasen.")
        return
    
    # Välj källan (CLAIM som ska referera)
    claim_options = format_claim_options(claims)
    selected_claim_index = claim_options.index(select_from_menu("Välj CLAIM (källan):", claim_options))
    selected_claim = claims[selected_claim_index]
    
    # Välj target-typ
    target_type = select_from_menu("Välj typ av target:", TARGET_TYPES)
    
    if target_type == "CLAIM":
        # Filtrera bort den valda claimen
        other_claims = [c for c in claims if c["id"] != selected_claim["id"]]
        if not other_claims:
            print("Det finns inga andra CLAIM att referera till.")
            return
        other_claim_options = format_claim_options(other_claims)
        selected_index = other_claim_options.index(select_from_menu("Välj CLAIM:", other_claim_options))
        target = other_claims[selected_index]
        create_reference(selected_claim["id"], target["id"], "CLAIM")
        
    elif target_type == "NPC":
        npcs = get_all_npcs()
        if not npcs:
            print("Det finns inga NPCs i databasen.")
            return
        npc_name = select_from_menu("Välj NPC:", npcs)
        create_reference(selected_claim["id"], npc_name, "NPC")
        
    else:  # OBJECT eller PLACE
        constants = get_all_constants()
        # Filtrera på vald typ
        filtered = [c for c in constants if c["type"] == target_type]
        if not filtered:
            print(f"Det finns inga {target_type} i databasen.")
            return
        options = [c["name"] for c in filtered]
        selected_name = select_from_menu(f"Välj {target_type}:", options)
        selected_index = options.index(selected_name)
        target = filtered[selected_index]
        create_reference(selected_claim["id"], target["id"], target_type)

if __name__ == "__main__":
    main()
