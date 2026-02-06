from db_utils import get_all_npcs, select_from_menu, confirm_action, delete_npc

def main():
    npcs = get_all_npcs()
    
    if not npcs:
        print("Det finns inga NPCs i databasen.")
        return
    
    # Välj NPC att ta bort
    name = select_from_menu("Välj NPC att ta bort:", npcs)
    
    # Bekräfta borttagning
    if confirm_action(f"Är du säker på att du vill ta bort '{name}' och alla dess relationer?"):
        delete_npc(name)
    else:
        print("Avbruten.")

if __name__ == "__main__":
    main()
