# backend/entity_extractor.py
import re
from typing import Dict, Any

RE_AIRPORT = re.compile(r'\b([A-Z]{3})\b')
# Flight numbers: UA123, BA155, 802 — but NOT 2025 (year)
RE_FLIGHT = re.compile(r'\b([A-Z]{2}\d{1,4}|\d{1,3})\b')



RE_DATE = re.compile(r'\b(20\d{2}-\d{2}-\d{2}|20\d{2}/\d{2}/\d{2}|tomorrow|today|on\s+\w+\s+\d{1,2})\b', re.I)
RE_INT = re.compile(r'\b(\d{1,4})\b')

def extract_entities(query: str) -> Dict[str, Any]:
    q = query.strip()
    entities = {}
    # airports (IATA)
    airports = RE_AIRPORT.findall(query)
    if airports:
        # heuristics: if two codes found, set origin/dest
        if len(airports) >= 2:
            entities['origin'] = airports[0]
            entities['destination'] = airports[1]
        else:
            entities['airport_candidates'] = airports
    # flight number
    # flight number
    fl = RE_FLIGHT.search(query)
    if fl:
        candidate = fl.group(1)

    # ignore numbers that appear inside date (e.g., 2025-05-18)
        d = RE_DATE.search(query)
        if d and candidate in d.group(1):
            pass  # skip (it's part of a date)
        else:
            entities['flight_number'] = candidate

        # filter out years
            if candidate.isdigit() and 2000 <= int(candidate) <= 2099:
                del entities['flight_number']
    # date
    d = RE_DATE.search(query)
    if d:
        entities['date'] = d.group(1)
    # small numeric extraction (e.g., "delay > 30")
    nums = [int(x) for x in RE_INT.findall(query)]
    if nums:
        entities['numbers'] = nums
    # simple class extraction
    if "economy" in q:
        entities['class'] = "Economy"
    if "business" in q:
        entities['class'] = "Business"
    return entities
