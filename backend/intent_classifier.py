# backend/intent_classifier.py
import re

# Regex patterns
RE_DATE = re.compile(r'\b(20\d{2}|tomorrow|today|on\s+\w+\s+\d{1,2})\b', re.I)

# Detect IATA airport codes (3 capital letters, not part of a longer word)
RE_AIRPORT = re.compile(r'\b([A-Z]{3})(?![A-Za-z])\b')

# Detect flight numbers: e.g., UA123, LH99, EK203, or 3-5 digit flight IDs
RE_FLIGHT = re.compile(r'\b([A-Z]{2}\d{1,4}|\b\d{3,5}\b)\b')

# Keyword groups
KW_FLIGHT_SEARCH = ["flight", "flights", "from", "to", "available", "schedule"]
KW_DELAY = ["delay", "delayed", "late", "on-time", "on time"]
KW_CANCEL = ["cancel", "cancelled", "canceled", "cancellation"]
KW_ROUTE = ["route", "routes", "pair"]
KW_AIRLINE = ["airline", "carrier", "airways"]
KW_COMPLAINT = ["complaint", "complaints", "review", "reviews", "issue"]
KW_AVAIL = ["seat", "seats", "availability", "available seats", "class", "economy", "business", "first"]
KW_CONNECT = ["connect", "connecting", "connection", "layover", "stop", "one stop"]
KW_RECOMMEND = ["recommend", "best", "least risky", "suggest", "cheap", "safest"]

def classify_intent_rule_based(query: str) -> str:
    q = query.lower()

    if any(kw in q for kw in KW_COMPLAINT):
        return "complaints_search"

    if any(kw in q for kw in KW_CONNECT):
        return "connecting_flights"

    if any(kw in q for kw in KW_AVAIL):
        return "availability"

    if any(kw in q for kw in KW_RECOMMEND):
        return "recommendation"

    if any(kw in q for kw in KW_CANCEL):
        return "cancellation_query"

    if any(kw in q for kw in KW_DELAY):
        return "delay_query"

    # Route stats queries
    if "avg delay" in q or "average delay" in q or \
       ("route" in q and ("avg" in q or "average" in q or "p90" in q)):
        return "route_stats"

    if any(kw in q for kw in KW_AIRLINE):
        return "airline_performance"

    # Generic flight search triggers
    if ("from" in q and "to" in q) or RE_AIRPORT.search(query) \
       or any(kw in q for kw in KW_FLIGHT_SEARCH):
        return "flight_search"

    # If a date is detected, assume search
    if RE_DATE.search(query):
        return "flight_search"

    return "unknown"

