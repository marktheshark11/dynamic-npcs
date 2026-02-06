from db_utils import get_all_npcs, get_all_groups, select_from_menu, create_membership

def main():
    # Kontrollera om det finns grupper först
    groups = get_all_groups()
    
    if not groups:
        print("Det finns inga grupper i databasen. Skapa en grupp först.")
        return
    
    # Hämta alla NPCs
    npcs = get_all_npcs()
    
    if not npcs:
        print("Det finns inga NPCs i databasen.")
        return
    
    # Välj NPC
    npc_name = select_from_menu("Välj NPC:", npcs)
    
    # Välj grupp
    group_name = select_from_menu("Välj grupp:", groups)
    
    # Skapa medlemskap
    create_membership(npc_name, group_name)

if __name__ == "__main__":
    main()
