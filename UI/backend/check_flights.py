# backend/check_flights.py
from graph_connector import run_cypher

print("=== Checking Flight Numbers ===\n")

query = """
MATCH (f:Flight)
RETURN DISTINCT f.flight_number AS flight_number
ORDER BY flight_number
LIMIT 20
"""

results = run_cypher(query)

print("Sample flight numbers in your database:")
for r in results:
    print(f"  {r['flight_number']}")

print(f"\nTotal shown: {len(results)}")
print("\n✅ Use one of these flight numbers in your queries!")