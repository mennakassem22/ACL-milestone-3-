# backend/entity_extractor.py - ENHANCED VERSION

import re
from typing import Dict, Any, List

# ============================================================================
# REGEX PATTERNS - More robust and accurate 
#short for (Regular Expression) is a powerful pattern-matching language used to search, extract, 
# and validate text based on specific patterns.
# ============================================================================

# Airport codes: 3 capital letters, not part of longer word
RE_AIRPORT = re.compile(r'\b([A-Z]{3})(?![A-Za-z])\b')

# Flight numbers: Airline code + digits (e.g., EK305, UA41) or standalone 3-5 digits
RE_FLIGHT = re.compile(r'\b([A-Z]{2}\d{1,4}|\d{3,5})\b')

# Dates: various formats
RE_DATE = re.compile(
    r'\b(20\d{2}-\d{2}-\d{2}|20\d{2}/\d{2}/\d{2}|tomorrow|today|on\s+\w+\s+\d{1,2})\b',
    re.I
)

# Numbers for limits, delays, etc.
RE_INT = re.compile(r'\b(\d{1,3})\b')

# Common airport/city names that should be mapped to codes
CITY_TO_AIRPORT = {
    'dubai': 'DXB',
    'cairo': 'CAI',
    'london': 'LHR',
    'new york': 'JFK',
    'los angeles': 'LAX',
    'chicago': 'ORD',
    'paris': 'CDG',
    'tokyo': 'NRT',
    'singapore': 'SIN',
    'hong kong': 'HKG',
    'sydney': 'SYD',
    'san francisco': 'SFO',
    'miami': 'MIA',
    'boston': 'BOS',
    'atlanta': 'ATL',
    'dallas': 'DFW',
    'denver': 'DEN',
    'seattle': 'SEA',
}

# Common words to exclude from being interpreted as airport codes
EXCLUDED_WORDS = {
    'AND', 'THE', 'FOR', 'ARE', 'ALL', 'CAN', 'GET', 'HAS', 'HAD',
    'WAS', 'HER', 'HIS', 'OUR', 'OUT', 'MAY', 'DAY', 'WAY', 'NEW',
    'OLD', 'TOP', 'LOW', 'BIG', 'BAD', 'GOD', 'NOW', 'HOW', 'WHY',
    'WHO', 'BUT', 'NOT', 'YET', 'FAR', 'FEW', 'TOO', 'YES', 'TWO'
}

# Keywords that indicate specific query types (helps with context)
DELAY_KEYWORDS = ['delay', 'delayed', 'late', 'on-time', 'ontime', 'punctual']
QUALITY_KEYWORDS = ['best', 'worst', 'good', 'bad', 'comfortable', 'excellent', 'poor', 'quality']
SATISFACTION_KEYWORDS = ['satisfaction', 'rating', 'review', 'feedback', 'complaint']


def extract_entities(query: str) -> Dict[str, Any]:
    """
    Extract entities from user query with enhanced accuracy.
    
    Args:
        query: User's natural language query
    
    Returns:
        Dictionary of extracted entities
    """
    q = query.strip()
    q_lower = q.lower()
    entities: Dict[str, Any] = {}
    
    # ----------------------------- 
    # 1) Extract airports (IATA codes)
    # ----------------------------- 
    airports = _extract_airports(query, q_lower)
    
    if airports:
        if len(airports) >= 2:
            entities['origin'] = airports[0]
            entities['destination'] = airports[1]
        elif len(airports) == 1:
            # Single airport - might be origin or destination
            entities['airport_candidates'] = airports
    
    # ----------------------------- 
    # 2) Extract flight numbers
    # ----------------------------- 
    flight_num = _extract_flight_number(query, q_lower)
    if flight_num:
        entities['flight_number'] = flight_num
    
    # ----------------------------- 
    # 3) Extract dates
    # ----------------------------- 
    date = _extract_date(query)
    if date:
        entities['date'] = date
    
    # ----------------------------- 
    # 4) Extract limit/count
    # ----------------------------- 
    limit = _extract_limit(q_lower)
    if limit:
        entities['limit'] = limit
    
    # ----------------------------- 
    # 5) Extract passenger class
    # ----------------------------- 
    passenger_class = _extract_passenger_class(q_lower)
    if passenger_class:
        entities['class'] = passenger_class
    
    # ----------------------------- 
    # 6) Extract query context/intent hints
    # ----------------------------- 
    context = _extract_query_context(q_lower)
    if context:
        entities['context'] = context
    
    return entities


def _extract_airports(query: str, query_lower: str) -> List[str]:
    """
    Extract airport codes with intelligent filtering.
    Also handles city names mapped to airport codes.
    """
    airports = []
    
    # First, check for city names
    for city, code in CITY_TO_AIRPORT.items():
        if city in query_lower:
            airports.append(code)
    
    # Then check for IATA codes
    iata_matches = RE_AIRPORT.findall(query)
    for code in iata_matches:
        # Exclude common English words
        if code not in EXCLUDED_WORDS and code not in airports:
            airports.append(code)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_airports = []
    for airport in airports:
        if airport not in seen:
            seen.add(airport)
            unique_airports.append(airport)
    
    return unique_airports


def _extract_flight_number(query: str, query_lower: str) -> str:
    """
    Extract flight number with better accuracy.
    Handles both airline codes (UA123) and standalone numbers (1004).
    """
    # Look for flight number patterns
    matches = RE_FLIGHT.findall(query)
    
    for match in matches:
        # Skip if it's a year
        if match.isdigit() and 2000 <= int(match) <= 2099:
            continue
        
        # Skip if it's part of a date
        date_match = RE_DATE.search(query)
        if date_match and match in date_match.group(1):
            continue
        
        # Check if query mentions "flight" near this number
        # This helps avoid false positives
        pattern = rf'\bflight\s*\S*\s*{re.escape(match)}\b'
        if re.search(pattern, query_lower):
            return match
        
        # If it's an airline code format (letters + numbers), accept it
        if not match.isdigit():
            return match
        
        # For standalone numbers, check context
        # Accept if in range 1-9999 (typical flight numbers)
        if match.isdigit():
            num = int(match)
            if 1 <= num <= 9999:
                return match
    
    return None


def _extract_date(query: str) -> str:
    """Extract date from query."""
    date_match = RE_DATE.search(query)
    if date_match:
        return date_match.group(1)
    return None


def _extract_limit(query_lower: str) -> int:
    """
    Extract limit/count with better context awareness.
    Looks for patterns like "top 5", "show 10", "best 3", etc.
    """
    # Check for explicit limit phrases
    limit_patterns = [
        r'top\s+(\d+)',
        r'best\s+(\d+)',
        r'worst\s+(\d+)',
        r'show\s+(\d+)',
        r'list\s+(\d+)',
        r'give\s+(?:me\s+)?(\d+)',
        r'find\s+(\d+)',
        r'(\d+)\s+flights',
        r'(\d+)\s+results',
    ]
    
    for pattern in limit_patterns:
        match = re.search(pattern, query_lower)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 100:  # Reasonable limit range
                return num
    
    # Default limit based on query type
    if any(word in query_lower for word in ['all', 'every', 'complete']):
        return 50  # Larger limit for comprehensive queries
    elif any(word in query_lower for word in ['top', 'best', 'worst']):
        return 5   # Smaller limit for ranked queries
    
    return 10  # Default


def _extract_passenger_class(query_lower: str) -> str:
    """Extract passenger class with better accuracy."""
    # Check in order of specificity (most specific first)
    if "premium economy" in query_lower:
        return "Premium Economy"
    elif "first class" in query_lower or "first-class" in query_lower:
        return "First"
    elif "business class" in query_lower or "business" in query_lower:
        return "Business"
    elif "economy class" in query_lower or "economy" in query_lower:
        return "Economy"
    
    return None


def _extract_query_context(query_lower: str) -> List[str]:
    """
    Extract query context hints (what the user cares about).
    This helps understand user intent better.
    """
    context = []
    
    # Check for delay-related queries
    if any(keyword in query_lower for keyword in DELAY_KEYWORDS):
        context.append('delay_focused')
    
    # Check for quality-related queries
    if any(keyword in query_lower for keyword in QUALITY_KEYWORDS):
        context.append('quality_focused')
    
    # Check for satisfaction-related queries
    if any(keyword in query_lower for keyword in SATISFACTION_KEYWORDS):
        context.append('satisfaction_focused')
    
    # Check for comparison queries
    if any(word in query_lower for word in ['compare', 'versus', 'vs', 'vs.', 'better', 'difference']):
        context.append('comparison')
    
    # Check for recommendation queries
    if any(word in query_lower for word in ['recommend', 'suggest', 'should', 'which one']):
        context.append('recommendation')
    
    return context


def validate_entities(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and clean extracted entities.
    Ensures entities make sense together.
    """
    # If origin and destination are the same, remove destination
    if 'origin' in entities and 'destination' in entities:
        if entities['origin'] == entities['destination']:
            del entities['destination']
    
    # Ensure limit is reasonable
    if 'limit' in entities:
        if entities['limit'] < 1:
            entities['limit'] = 5
        elif entities['limit'] > 100:
            entities['limit'] = 100
    
    return entities


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Testing Enhanced Entity Extractor ===\n")
    
    test_queries = [
        # Airport extraction
        "Show me the best flights from DXB to CAI with less delay",
        "Flights from Dubai to Cairo",
        "Find flights ORX to LAX",
        
        # Flight number extraction
        "Show complaints about flight 1004",
        "Details for flight UA123",
        "Tell me about flight 103",
        
        # Limit extraction
        "Show top 5 flights from ORX to LAX",
        "Give me 3 best flights",
        "List all flights",
        
        # Context extraction
        "Find comfortable flights with good food",
        "Which flights are always delayed?",
        "Compare flight 1004 and 1005",
        "Recommend the best flight from ORX to LAX",
        
        # Class extraction
        "Business class flights to London",
        "First class from Dubai to Cairo",
        
        # Complex queries
        "Show me top 10 business class flights from DXB to CAI with minimal delays and high satisfaction",
        "What are the 5 worst delayed flights from ORX to LAX?",
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Test {idx}: {query}")
        print('='*70)
        
        entities = extract_entities(query)
        entities = validate_entities(entities)
        
        print("Extracted Entities:")
        for key, value in entities.items():
            print(f"  {key}: {value}")
        
        if not entities:
            print("  (No entities extracted)")
    
    print("\n\nEnhancement Summary:")
    print("  • City name recognition (Dubai → DXB)")
    print("  • Better flight number detection")
    print("  • Context-aware limit extraction")
    print("  • Query context hints (delay_focused, quality_focused, etc.)")
    print("  • Validation and cleaning")
    print("  • Excluded common words from airport codes")