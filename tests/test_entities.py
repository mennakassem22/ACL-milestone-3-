from entity_extractor import extract_entities

tests = [
    "Find flights from CAI to DXB",
    "Show delay for flight UA404",
    "I want flights from JFK to LAX on 2025-05-18",
    "Complaints about flight 802",
    "Find business seats on flight BA155",
    "Show connecting flights from CAI to LHR",
]

for q in tests:
    entities = extract_entities(q)
    print(f"Query: {q}")
    print(f"Entities → {entities}")
    print("-" * 40)
# backend/test_entities.py