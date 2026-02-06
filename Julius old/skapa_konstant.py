from db_utils import create_object, create_place, select_from_menu

def main():
    konstant_type = select_from_menu("Välj typ av konstant:", ["OBJECT", "PLACE"])
    
    if konstant_type == "OBJECT":
        name = input("Ange namnet på objektet: ")
        create_object(name)
    else:
        name = input("Ange namnet på platsen: ")
        create_place(name)

if __name__ == "__main__":
    main()
