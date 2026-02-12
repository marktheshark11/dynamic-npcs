# DONT USE 
# import os
# from dotenv import load_dotenv
# from neo4j import GraphDatabase

# def create_vector_index():
#     load_dotenv()
#     db_user = os.getenv("NEO4J_USER")
#     db_password = os.getenv("NEO4J_PASSWORD")
#     db_uri = os.getenv('NEO4J_URI')

#     if(db_uri):
#       driver = GraphDatabase.driver(db_uri, auth=(db_user, db_password))

#     with driver.session() as session:
#         # Kontrollera om indexet redan finns
#         result = session.run("SHOW INDEXES")
#         existing_indexes = [record["name"] for record in result]
        
#         if "claim_index" in existing_indexes:
#             print("✓ Vektorindex 'claim_index' finns redan")
#         else:
#             # Skapa vektorindex för CLAIM.embedding
#             # 1024 dimensioner för mxbai-embed-large modellen
#             session.run("""
#                 CREATE VECTOR INDEX claim_index IF NOT EXISTS
#                 FOR (c:CLAIM)
#                 ON c.embedding
#                 OPTIONS {indexConfig: {
#                     `vector.dimensions`: 1024,
#                     `vector.similarity_function`: 'cosine'
#                 }}
#             """)
#             print("✓ Vektorindex 'claim_index' skapat!")
#             print("  - Dimensioner: 1024")
#             print("  - Similarity function: cosine")

#     driver.close()
#     print("\nKlart!")

# if __name__ == "__main__":
#     create_vector_index()
