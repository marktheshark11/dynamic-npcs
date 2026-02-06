from db_utils import update_all_claim_embeddings, get_all_claims, update_claim_embedding, select_from_menu

def main():
    print("=" * 50)
    print("         SKAPA/UPPDATERA EMBEDDINGS")
    print("=" * 50)
    
    options = [
        "Uppdatera ALLA claims",
        "Uppdatera en specifik claim",
        "Avbryt"
    ]
    
    choice = select_from_menu("Vad vill du göra?", options)
    
    if choice == "Uppdatera ALLA claims":
        update_all_claim_embeddings()
        
    elif choice == "Uppdatera en specifik claim":
        claims = get_all_claims()
        if not claims:
            print("\n⚠ Inga claims hittades")
            return
        
        claim_options = [f"[{c['veracity']}] {c['content']}" for c in claims]
        selected = select_from_menu("Välj claim att uppdatera:", claim_options)
        selected_index = claim_options.index(selected)
        claim = claims[selected_index]
        
        update_claim_embedding(claim["id"])
        
    else:
        print("\nAvbrutet.")

if __name__ == "__main__":
    main()
