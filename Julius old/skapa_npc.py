from db_utils import create_npc, create_group, select_from_menu

def main():
    node_type = select_from_menu("Vad vill du skapa?", ["NPC", "GROUP"])
    
    if node_type == "NPC":
        name = input("Ange namnet på NPC:n som ska skapas: ")
        create_npc(name)
    else:
        name = input("Ange namnet på gruppen som ska skapas: ")
        create_group(name)

if __name__ == "__main__":
    main()