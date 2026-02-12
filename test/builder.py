import os
from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from neo4j import GraphDatabase

from node_builder import NodeBuilder




def main():
  load_dotenv()  # reads variables from a .env file and sets them in os.environ
  db_user = os.getenv("NEO4J_USER")
  db_password = os.getenv("NEO4J_PASSWORD")
  db_uri = os.getenv('NEO4J_URI')


  # driver = GraphDatabase.driver(
  #     "neo4j+s://7ab9efca.databases.neo4j.io", 
  #     auth=("neo4j", "9k6CKG5Mei8KtoVKtZqbre3EZBbuWRQ_SPzRkNGINpE")
  # )
  if db_uri:
    driver = GraphDatabase.driver(
        db_uri, 
        auth=(db_user, db_password)
    )
  else: return

  embed_model = OllamaEmbeddings(model="mxbai-embed-large")
  node_builder = NodeBuilder(driver, embed_model)

  while True:
    print('1: Skapa en ny NPC nod')
    print('2: Ta bort en NPC')
    print('3: Redigera en NPC')
    print('4: Skapa en ny CLAIM')
    print('5: Visa alla CLAIMs')
    print('6: Koppla NPC till CLAIM (skapa OPINION)')
    print('7: Ta bort en CLAIM')
    print('8: Redigera en CLAIM')
    print('0: Avsluta')    
    function_i = input('Välj: ')
    if function_i == '0':
      break
    elif function_i == '1':
      id_i = input('id: ')
      name_i = input('namn: ')
      age_i = int(input('ålder: '))
      personality_i = input('personlighet: ')
      node_builder.create_npc_node(id_i, name_i, age_i, personality_i)
    elif function_i == '2':
      npcs = node_builder.list_all_npcs()
      if not npcs:
        print("\n✗ Inga NPCs hittades")
        continue
      
      print("\n=== Alla NPCs ===")
      for idx, npc in enumerate(npcs, 1):
        print(f"{idx}. ID: {npc['id']}, Namn: {npc['name']}, Ålder: {npc['age']}, Personlighet: {npc['personality']}")
      
      choice = input('\nVälj nummer eller skriv ID: ')
      try:
        # Check if user entered a number (index) or ID
        if choice.isdigit() and 1 <= int(choice) <= len(npcs):
          selected_npc = npcs[int(choice) - 1]
          id_i = selected_npc['id']
        else:
          id_i = choice
        node_builder.delete_npc(id_i)
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")
    elif function_i == '4':
      content_i = input('content: ')
      is_rel = input('relation? (j/n): ').lower() == 'j'
      relation_type = 'relation' if is_rel else None
      node_builder.create_claim(content_i, relation_type)
    elif function_i == '3':
      npcs = node_builder.list_all_npcs()
      if not npcs:
        print("\n✗ Inga NPCs hittades")
        continue
      
      print("\n=== Alla NPCs ===")
      for idx, npc in enumerate(npcs, 1):
        print(f"{idx}. ID: {npc['id']}, Namn: {npc['name']}, Ålder: {npc['age']}, Personlighet: {npc['personality']}")
      
      choice = input('\nVälj nummer eller skriv ID: ')
      try:
        # Check if user entered a number (index) or ID
        if choice.isdigit() and 1 <= int(choice) <= len(npcs):
          selected_npc = npcs[int(choice) - 1]
          id_i = selected_npc['id']
        else:
          id_i = choice
        
        name_i = input('namn (lämna tom för ingen ändring): ')
        age_i = input('ålder (lämna tom för ingen ändring): ')
        personality_i = input('personlighet (lämna tom för ingen ändring): ')
        
        # Convert empty strings to None
        name_i = name_i if name_i else None
        age_i = int(age_i) if age_i else None
        personality_i = personality_i if personality_i else None
        
        node_builder.edit_npc(id_i, name_i, age_i, personality_i)
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")
    elif function_i == '5':
      claims = node_builder.list_all_claims()
      if not claims:
        print("\n✗ Inga CLAIMs hittades")
        continue
      
      print("\n=== Alla CLAIMs ===")
      for claim in claims:
        claim_id = claim['claim_id'] if claim['claim_id'] else 'N/A'
        content = claim['content'][:60] + '...' if len(claim['content']) > 60 else claim['content']
        claim_type = f" [{claim['type']}]" if claim['type'] else ""
        print(f"{claim_id}{claim_type}: {content}")
    
    elif function_i == '6':
      # Visa NPCs
      npcs = node_builder.list_all_npcs()
      if not npcs:
        print("\n✗ Inga NPCs hittades")
        continue
      
      print("\n=== Välj NPC ===")
      for idx, npc in enumerate(npcs, 1):
        print(f"{idx}. ID: {npc['id']}, Namn: {npc['name']}")
      
      npc_choice = input('\nVälj nummer eller skriv ID: ')
      try:
        if npc_choice.isdigit() and 1 <= int(npc_choice) <= len(npcs):
          npc_id = npcs[int(npc_choice) - 1]['id']
        else:
          npc_id = npc_choice
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")
        continue
      
      # Visa claims
      claims = node_builder.list_all_claims()
      if not claims:
        print("\n✗ Inga CLAIMs hittades")
        continue
      
      print("\n=== Välj CLAIM ===")
      for idx, claim in enumerate(claims, 1):
        claim_id = claim['claim_id'] if claim['claim_id'] else 'N/A'
        content = claim['content'][:50] + '...' if len(claim['content']) > 50 else claim['content']
        print(f"{idx}. {claim_id}: {content}")
      
      claim_choice = input('\nVälj nummer: ')
      try:
        if claim_choice.isdigit() and 1 <= int(claim_choice) <= len(claims):
          claim_id = claims[int(claim_choice) - 1]['claim_id']
        else:
          print("\n✗ Ogiltigt val")
          continue
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")
        continue
      
      # Hämta belief_in och openness
      print("\nAnge belief_in (-1 till 1, där -1 = tror inte alls, 0 = neutral, 1 = tror starkt):")
      belief_in = float(input('belief_in: '))
      if belief_in < -1 or belief_in > 1:
        print("\n✗ Värdet måste vara mellan -1 och 1")
        continue
      
      print("\nAnge openness (-1 till 1, där -1 = stängd, 0 = neutral, 1 = mycket öppen):")
      openness = float(input('openness: '))
      if openness < -1 or openness > 1:
        print("\n✗ Värdet måste vara mellan -1 och 1")
        continue
      
      node_builder.create_opinion(npc_id, claim_id, belief_in, openness)
    
    elif function_i == '7':
      # Visa claims
      claims = node_builder.list_all_claims()
      if not claims:
        print("\n✗ Inga CLAIMs hittades")
        continue
      
      print("\n=== Välj CLAIM att ta bort ===")
      for idx, claim in enumerate(claims, 1):
        claim_id = claim['claim_id'] if claim['claim_id'] else 'N/A'
        content = claim['content'][:50] + '...' if len(claim['content']) > 50 else claim['content']
        claim_type = f" [{claim['type']}]" if claim['type'] else ""
        print(f"{idx}. {claim_id}{claim_type}: {content}")
      
      claim_choice = input('\nVälj nummer: ')
      try:
        if claim_choice.isdigit() and 1 <= int(claim_choice) <= len(claims):
          selected_claim = claims[int(claim_choice) - 1]
          claim_id = selected_claim['claim_id']
          
          # Bekräfta borttagning
          confirm = input(f"\nÄr du säker på att du vill ta bort CLAIM {claim_id}? (j/n): ")
          if confirm.lower() == 'j':
            node_builder.delete_claim(claim_id)
          else:
            print("\nAvbruten.")
        else:
          print("\n✗ Ogiltigt val")
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")
    
    elif function_i == '8':
      # Visa claims
      claims = node_builder.list_all_claims()
      if not claims:
        print("\n✗ Inga CLAIMs hittades")
        continue
      
      print("\n=== Välj CLAIM att redigera ===")
      for idx, claim in enumerate(claims, 1):
        claim_id = claim['claim_id'] if claim['claim_id'] else 'N/A'
        content = claim['content'][:50] + '...' if len(claim['content']) > 50 else claim['content']
        claim_type = f" [{claim['type']}]" if claim['type'] else ""
        print(f"{idx}. {claim_id}{claim_type}: {content}")
      
      claim_choice = input('\nVälj nummer: ')
      try:
        if claim_choice.isdigit() and 1 <= int(claim_choice) <= len(claims):
          selected_claim = claims[int(claim_choice) - 1]
          claim_id = selected_claim['claim_id']
          
          print(f"\nRedigera CLAIM {claim_id}")
          print(f"Nuvarande content: {selected_claim['content']}")
          print(f"Nuvarande type: {selected_claim['type'] if selected_claim['type'] else '(ingen)'}")
          
          # Hämta nya värden
          new_content = input('\nNytt content (lämna tom för ingen ändring): ')
          new_content = new_content if new_content else None
          
          type_choice = input('Ny type - 1: relation, 2: ingen type, 3: behåll: ')
          if type_choice == '1':
            new_type = 'relation'
          elif type_choice == '2':
            new_type = ''  # Tom sträng = ta bort type
          else:
            new_type = None  # None = behåll nuvarande
          
          if new_content is not None or new_type is not None:
            node_builder.edit_claim(claim_id, new_content, new_type)
          else:
            print("\n✗ Inga ändringar gjorda")
        else:
          print("\n✗ Ogiltigt val")
      except (ValueError, IndexError):
        print("\n✗ Ogiltigt val")

if __name__ == "__main__":
  main()

