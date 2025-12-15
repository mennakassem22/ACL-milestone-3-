from graph_connector import run_cypher

print("=== Airports ===")
print(run_cypher("MATCH (a:Airport) RETURN a LIMIT 20;"))

print("\n=== Flights ===")
print(run_cypher("MATCH (f:Flight) RETURN f LIMIT 20;"))

print("\n=== Journeys ===")
print(run_cypher("MATCH (j:Journey) RETURN j LIMIT 20;"))
