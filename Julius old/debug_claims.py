from db_utils import driver, create_query_embedding

# Test vektorsökning
query = "Vem är din mamma?"
query_embedding = create_query_embedding(query)

with driver.session() as session:
    # Hämta Brunos tillgängliga claim IDs
    result = session.run("""
        MATCH (n:NPC {name: "Bruno"})
        OPTIONAL MATCH (n)-[:BELIEF]->(c1:CLAIM)
        OPTIONAL MATCH (n)-[:MEMBER_OF]->(g:GROUP)-[:BELIEF]->(c2:CLAIM)
        WITH collect(DISTINCT c1) + collect(DISTINCT c2) AS all_claims
        UNWIND all_claims AS c
        WITH c WHERE c IS NOT NULL AND c.embedding IS NOT NULL
        RETURN DISTINCT id(c) AS id
    """)
    accessible_ids = [r["id"] for r in result]
    print(f"Bruno har tillgång till {len(accessible_ids)} claims med IDs: {accessible_ids}")
    
    # Test vektorindex utan filter
    print("\n--- Vektorsökning UTAN filter ---")
    result2 = session.run("""
        CALL db.index.vector.queryNodes('claim_index', 5, $query_vector)
        YIELD node, score
        RETURN id(node) AS id, node.content AS content, score
    """, query_vector=query_embedding)
    for r in result2:
        in_accessible = "✓" if r["id"] in accessible_ids else "✗"
        print(f"  {in_accessible} [{r['score']:.3f}] {r['content'][:50]}... (id: {r['id']})")
    
    # Test med filter
    print("\n--- Vektorsökning MED filter ---")
    result3 = session.run("""
        CALL db.index.vector.queryNodes('claim_index', 9, $query_vector)
        YIELD node, score
        WHERE id(node) IN $accessible_ids
        RETURN id(node) AS id, node.content AS content, score
        LIMIT 3
    """, query_vector=query_embedding, accessible_ids=accessible_ids)
    results = list(result3)
    print(f"  Hittade {len(results)} claims")
    for r in results:
        print(f"  [{r['score']:.3f}] {r['content'][:50]}...")
