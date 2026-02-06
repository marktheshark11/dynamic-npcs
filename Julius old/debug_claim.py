from db_utils import driver

with driver.session() as s:
    r = s.run("MATCH (c:CLAIM)-[:REFERENCE]->(t) WHERE id(c) = 20 RETURN t.name AS name, labels(t) AS labels")
    refs = list(r)
    print("Claim 20 (kärleksbrev) refererar till:")
    for x in refs:
        print(f"  {x['name']} ({x['labels']})")
    if not refs:
        print("  (Inga REFERENCE-relationer!)")
