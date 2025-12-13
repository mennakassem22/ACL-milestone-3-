# backend/test_intent.py

from intent_classifier import classify_intent_rule_based

tests = [
    "Show flights from CAI to DXB",
    "What is the average delay for flights from JFK to LAX?",
    "Show me cancelled flights",
    "Recommend the least risky flight from ORD to DEN",
    "Show complaints about flight UA123",
    "How many business seats are available on flight 802?",
    "Find connecting flights from CAI to LHR",
    "Tell me about airline performance for Boeing 777"
]

for q in tests:
    intent = classify_intent_rule_based(q)
    print(f"Query: {q}")
    print(f"Intent → {intent}")
    print("-" * 40)
