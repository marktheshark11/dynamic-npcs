from db_utils import (
    get_all_npcs, get_all_groups, get_entity_knowledge, select_from_menu, 
    confirm_action, delete_knowledge
)

def format_knowledge_options(knowledge_list):
    """Formatera kunskaps-listan för visning i menyn."""
    return [f"[{k['veracity']}] \"{k['content']}\" (belief: {k['belief']}, stance: {k['stance']})" 
            for k in knowledge_list]

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
    
    # Hämta entitetens kunskaper
    knowledge_list = get_entity_knowledge(entity_name, entity_type)
    
    if not knowledge_list:
        print(f"\n{entity_name} har ingen kunskap i databasen.")
        return
    
    # Välj kunskap att ta bort
    knowledge_options = format_knowledge_options(knowledge_list)
    selected_index = knowledge_options.index(select_from_menu(
        f"Välj kunskap att ta bort från {entity_name}:", knowledge_options))
    selected_knowledge = knowledge_list[selected_index]
    
    # Bekräfta borttagning
    if confirm_action(f"Är du säker på att du vill ta bort denna kunskap?"):
        delete_knowledge(entity_name, entity_type, selected_knowledge["claim_id"])
    else:
        print("Avbruten.")

if __name__ == "__main__":
    main()
