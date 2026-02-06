from db_utils import create_claim, select_from_menu

def main():
    veracity = select_from_menu("Välj veracity för claim:", ["truth", "lie"])
    info = input("Ange informationen som ska skapas: ")
    create_claim(veracity, info)

if __name__ == "__main__":
    main()