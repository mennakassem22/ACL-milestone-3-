# backend/intent_classifier.py - FIXED VERSION

import re

# ============================================================================
# REGEX PATTERNS
# ============================================================================

RE_AIRPORT = re.compile(r'\b([A-Z]{3})(?![A-Za-z])\b')
RE_FLIGHT = re.compile(r'\b([A-Z]{2}\d{1,4}|\d{3,5})\b')
RE_DATE = re.compile(r'\b(20\d{2}|tomorrow|today|on\s+\w+\s+\d{1,2})\b', re.I)

# ============================================================================
# KEYWORD GROUPS - Organized by priority
# ============================================================================

# High priority - very specific intents
KW_COMPLAINT = ["complaint", "complaints", "feedback", "review", "reviews", "issue", "problem"]
KW_SATISFACTION = ["satisfaction", "rating", "rated", "score"]
KW_CONNECT = ["connect", "connecting", "connection", "layover", "stop", "one stop", "transfer"]
KW_RECOMMEND = ["recommend", "best", "suggest", "should i", "which flight", "top", "least risky", "safest"]
KW_COMPARISON = ["compare", "vs", "versus", "difference between", "better than"]

# Medium priority - moderately specific
KW_CANCEL = ["cancel", "cancelled", "canceled", "cancellation"]
KW_DELAY = ["delay", "delayed", "late", "on-time", "on time", "punctual", "punctuality"]
KW_ROUTE = ["route", "routes", "between", "avg delay", "average delay"]
KW_AIRLINE = ["airline", "carrier", "airways", "fleet", "aircraft"]
KW_AVAIL = ["seat", "seats", "availability", "available", "capacity", "class", "economy", "business", "first"]
KW_QUALITY = ["comfortable", "good", "bad", "worst", "excellent", "poor", "quality"]

# Low priority - general search
KW_FLIGHT_SEARCH = ["flight", "flights", "fly", "flying", "travel"]

# ============================================================================
# MAIN CLASSIFICATION FUNCTION
# ============================================================================

def classify_intent(query: str) -> str:
    """
    Classify user intent with improved accuracy.
    Checks from most specific to least specific.
    
    Args:
        query: User's natural language query
    
    Returns:
        Intent string matching keys in retriever.choose_template_for_intent()
    """
    q = query.lower().strip()
    
    # -------------------------
    # PRIORITY 1: Very Specific Intents
    # -------------------------
    
    # Satisfaction/Quality queries
    if any(kw in q for kw in KW_SATISFACTION):
        # Check if asking about specific flight
        if RE_FLIGHT.search(query):
            return "satisfaction_query"  # flight_satisfaction_stats
        return "quality_search"  # search_high_satisfaction
    
    # Complaints about specific flight
    if any(kw in q for kw in KW_COMPLAINT):
        if RE_FLIGHT.search(query):
            return "complaints_search"  # flight_complaints
        return "quality_search"  # Find low-rated flights
    
    # Comparison queries
    if any(kw in q for kw in KW_COMPARISON):
        return "comparison"  # compare_routes
    
    # Connection/layover queries
    if any(kw in q for kw in KW_CONNECT):
        return "connecting_flights"  # connecting_flights_one_stop
    
    # Recommendation queries (must be before flight_search)
    if any(kw in q for kw in KW_RECOMMEND):
        # Check if it's route-specific or general
        airports = RE_AIRPORT.findall(query)
        if len(airports) >= 2:
            return "recommendation"  # recommend_least_risky (route-specific)
        return "best_flights"  # recommend_best_flights (general)
    
    # Seat/class availability
    if any(kw in q for kw in KW_AVAIL):
        if RE_FLIGHT.search(query):
            return "availability"  # seat_availability
        return "flight_search"  # Find flights with class filter
    
    # -------------------------
    # PRIORITY 2: Moderately Specific Intents
    # -------------------------
    
    # Cancellation queries
    if any(kw in q for kw in KW_CANCEL):
        return "cancellation_query"  # top_cancelled_routes
    
    # Delay queries
    if any(kw in q for kw in KW_DELAY):
        # Route-level delay stats
        if "route" in q or "between" in q or len(RE_AIRPORT.findall(query)) >= 2:
            return "route_stats"  # avg_delay_per_route
        # Flight-level delay query
        if RE_FLIGHT.search(query):
            return "satisfaction_query"  # Get specific flight stats
        return "delay_query"  # delay_query (general)
    
    # Route statistics
    if any(kw in q for kw in KW_ROUTE):
        if "avg" in q or "average" in q or "stats" in q or "statistics" in q:
            return "route_stats"  # avg_delay_per_route
    
    # Fleet/airline performance
    if any(kw in q for kw in KW_AIRLINE):
        return "airline_performance"  # airline_performance
    
    # Quality-focused searches
    if any(kw in q for kw in KW_QUALITY):
        if "worst" in q or "bad" in q or "poor" in q:
            return "complaints_search"  # Find problem flights
        return "quality_search"  # search_high_satisfaction
    
    # -------------------------
    # PRIORITY 3: General Flight Search
    # -------------------------
    
    # Flight search with route
    airports = RE_AIRPORT.findall(query)
    if len(airports) >= 2:
        return "flight_search"  # find_flights_between
    
    # Flight search by flight number
    if RE_FLIGHT.search(query):
        # Check if asking about specific metrics
        if any(kw in q for kw in KW_DELAY + KW_SATISFACTION + KW_COMPLAINT):
            return "satisfaction_query"
        return "flight_search"
    
    # General flight search keywords
    if any(kw in q for kw in KW_FLIGHT_SEARCH):
        # Has origin/destination keywords
        if "from" in q or "to" in q:
            return "flight_search"
        # Has date
        if RE_DATE.search(query):
            return "flight_search"
        # General search
        return "fleet_search"  # search_by_fleet or fallback
    
    # -------------------------
    # FALLBACK: Unknown
    # -------------------------
    
    print(f"⚠️  Could not classify intent for: '{query}'")
    return "unknown"


# ============================================================================
# HELPER FUNCTION FOR DEBUGGING
# ============================================================================

def explain_classification(query: str) -> dict:
    """
    Explain why a query was classified a certain way.
    Useful for debugging.
    """
    intent = classify_intent(query)
    q = query.lower()
    
    explanation = {
        "query": query,
        "intent": intent,
        "detected_patterns": {}
    }
    
    # Check what patterns were detected
    if RE_AIRPORT.findall(query):
        explanation["detected_patterns"]["airports"] = RE_AIRPORT.findall(query)
    if RE_FLIGHT.search(query):
        explanation["detected_patterns"]["flight_number"] = RE_FLIGHT.findall(query)
    if RE_DATE.search(query):
        explanation["detected_patterns"]["date"] = RE_DATE.findall(query)
    
    # Check which keyword groups matched
    keyword_matches = []
    if any(kw in q for kw in KW_COMPLAINT):
        keyword_matches.append("complaints")
    if any(kw in q for kw in KW_DELAY):
        keyword_matches.append("delay")
    if any(kw in q for kw in KW_RECOMMEND):
        keyword_matches.append("recommendation")
    if any(kw in q for kw in KW_CONNECT):
        keyword_matches.append("connection")
    
    explanation["detected_patterns"]["keywords"] = keyword_matches
    
    return explanation


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Testing Enhanced Intent Classifier ===\n")
    
    test_cases = [
        # Flight search
        ("Show me flights from ORD to LAX", "flight_search"),
        ("Find available flights", "fleet_search"),
        ("Flights on December 15", "flight_search"),
        
        # Delays
        ("Which flights are always delayed?", "delay_query"),
        ("Show delay statistics for ORD to LAX route", "route_stats"),
        ("What's the average delay on this route?", "route_stats"),
        
        # Recommendations
        ("Recommend the best flight from DXB to CAI", "recommendation"),
        ("What are the top 5 flights?", "best_flights"),
        ("Which flight should I take?", "recommendation"),
        
        # Complaints/Satisfaction
        ("Show complaints about flight 1004", "complaints_search"),
        ("What's the satisfaction rating for flight UA123?", "satisfaction_query"),
        ("Find flights with good ratings", "quality_search"),
        
        # Connections
        ("Find connecting flights from ORD to LAX", "connecting_flights"),
        ("One stop flights to Cairo", "connecting_flights"),
        
        # Performance
        ("How is the Boeing 737 performing?", "airline_performance"),
        ("Fleet performance stats", "airline_performance"),
        
        # Comparison
        ("Compare routes from ORD", "comparison"),
        
        # Complex
        ("Show me the best 10 business class flights from DXB to CAI with minimal delays", "recommendation"),
        ("What are the worst delayed flights?", "delay_query"),
    ]
    
    print(f"Testing {len(test_cases)} queries...\n")
    
    correct = 0
    for query, expected in test_cases:
        result = classify_intent(query)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            correct += 1
        
        print(f"{status} Query: {query}")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")
        
        if result != expected:
            # Show explanation for failures
            exp = explain_classification(query)
            print(f"   Patterns: {exp['detected_patterns']}")
        
        print()
    
    print(f"\n{'='*70}")
    print(f"Accuracy: {correct}/{len(test_cases)} ({100*correct/len(test_cases):.1f}%)")
    print(f"{'='*70}")