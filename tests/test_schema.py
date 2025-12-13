from graph_connector import run_cypher

print("\n=== Node Labels ===")
print(run_cypher("CALL db.labels() YIELD label RETURN label;"))

print("\n=== Relationship Types ===")
print(run_cypher("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType;"))

print("\n=== Sample Properties per Label ===")
labels = run_cypher("CALL db.labels() YIELD label RETURN label;")
for row in labels:
    label = row["label"]
    print(f"\n--- {label} ---")
    q = f"MATCH (n:{label}) RETURN keys(n) AS props LIMIT 5;"
    print(run_cypher(q))
# backend/test_schema.py