from db_utils import delete_claim, get_all_claims, select_from_menu, confirm_action, delete_claim

def main():
    claim_list = get_all_claims()
    
    if not claim_list:
        print("Det finns inga CLAIM i databasen.")
        return
    
    # Skapa visningsalternativ med veracity och innehåll
    options = [f"[{claim['veracity']}] {claim['content']}" for claim in claim_list]
    
    # Välj information att ta bort
    selected = select_from_menu("Välj CLAIM att ta bort:", options)
    selected_index = options.index(selected)
    selected_claim = claim_list[selected_index]
    
    # Bekräfta borttagning
    if confirm_action(f"Är du säker på att du vill ta bort '{selected_claim['content']}'?"):
        delete_claim(selected_claim['id'])
    else:
        print("Avbruten.")

if __name__ == "__main__":
    main()
