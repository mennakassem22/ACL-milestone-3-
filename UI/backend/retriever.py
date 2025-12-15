# backend/retriever.py - ENHANCED VERSION

from graph_connector import run_cypher
from cypher_templates import TEMPLATES
from typing import List, Dict, Any
# In retriever.py, update choose_template_for_intent():

def choose_template_for_intent(intent: str) -> str:
    mapping = {
        # Exact matches from classifier
        "flight_search": "find_flights_between",
        "delay_query": "delay_query",
        "route_stats": "avg_delay_per_route",
        "cancellation_query": "top_cancelled_routes",
        "airline_performance": "airline_performance",
        "complaints_search": "flight_complaints",
        "satisfaction_query": "flight_satisfaction_stats",
        "availability": "seat_availability",
        "connecting_flights": "connecting_flights_one_stop",
        "recommendation": "recommend_least_risky",
        "best_flights": "recommend_best_flights",  # NEW
        "fleet_search": "search_by_fleet",  # NEW
        "quality_search": "search_high_satisfaction",  # NEW
        "comparison": "compare_routes",  # NEW
        "unknown": "fallback_query"
    }
    
    template = mapping.get(intent, "fallback_query")
    print(f"🎯 Intent '{intent}' → Template '{template}'")
    return template

def run_template(template_name: str, params: Dict[str, Any]) -> List[Dict]:
    """
    Execute a Cypher query template with given parameters.
    ENHANCED: Better error handling and parameter validation.
    
    Args:
        template_name: Name of the template from cypher_templates.py
        params: Dictionary of parameters to fill in the template
    
    Returns:
        List of dictionaries containing query results
    """
    if template_name not in TEMPLATES:
        print(f"⚠️  Warning: Template '{template_name}' not found. Using fallback.")
        template_name = "fallback_query"
    
    template = TEMPLATES[template_name]
    cypher = template["cypher"]
    required_params = template["params"]
    
    # Fill in missing params with safe defaults
    validated_params = validate_params(params, required_params, template_name)
    
    try:
        results = run_cypher(cypher, validated_params)
        print(f"✅ Query '{template_name}' returned {len(results)} results")
        return results
    except Exception as e:
        print(f"❌ Error executing template '{template_name}': {e}")
        # Try fallback query
        if template_name != "fallback_query":
            print("🔄 Attempting fallback query...")
            return run_template("fallback_query", {"limit": params.get("limit", 10)})
        return []


def validate_params(params: Dict[str, Any], required_params: List[str], template_name: str) -> Dict[str, Any]:
    """
    Validate and fill in missing parameters with sensible defaults.
    
    Args:
        params: User-provided parameters
        required_params: Required parameters for template
        template_name: Name of template (for context-aware defaults)
    
    Returns:
        Validated parameters dict
    """
    validated = params.copy()
    
    for param in required_params:
        if param not in validated or validated[param] is None:
            # Provide sensible defaults
            if param == "limit":
                validated[param] = 10
            elif param in ["origin", "destination"]:
                validated[param] = ""  # Empty string for optional route filters
            elif param == "fleet":
                validated[param] = ""
            elif param == "flight_no":
                validated[param] = ""
            elif param == "class":
                validated[param] = ""
            elif param == "min_score":
                validated[param] = 4.0  # For satisfaction queries
            else:
                validated[param] = None
    
    return validated


def expand_subgraph_for_flights(flight_numbers: List[str], depth: int = 1) -> List[Dict]:
    """
    Given a list of flight numbers, retrieve a richer subgraph around them.
    ENHANCED: More comprehensive data retrieval.
    
    Args:
        flight_numbers: List of flight numbers to expand around
        depth: How many hops away from the flights to retrieve (not used yet)
    
    Returns:
        List of dictionaries with detailed graph information
    """
    if not flight_numbers:
        return []
    
    # Clean flight numbers
    flight_numbers = [str(fn) for fn in flight_numbers if fn]
    
    if not flight_numbers:
        return []
    
    query = """
    MATCH (f:Flight)
    WHERE f.flight_number IN $flight_numbers
    OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(origin:Airport)
    OPTIONAL MATCH (f)-[:ARRIVES_AT]->(dest:Airport)
    OPTIONAL MATCH (j:Journey)-[:ON]->(f)
    WITH f, origin, dest, collect(j) AS journeys
    RETURN 
        f.flight_number AS flight_number,
        f.fleet_type_description AS fleet,
        origin.station_code AS origin_code,
        dest.station_code AS dest_code,
        size(journeys) AS journey_count,
        avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
        avg([j IN journeys | j.food_satisfaction_score]) AS avg_food,
        min([j IN journeys | j.arrival_delay_minutes]) AS min_delay,
        max([j IN journeys | j.arrival_delay_minutes]) AS max_delay,
        [j IN journeys[0..5] | {
            feedback_id: j.feedback_ID,
            delay: j.arrival_delay_minutes,
            food_score: j.food_satisfaction_score,
            passenger_class: j.passenger_class
        }] AS sample_journeys
    """
    
    try:
        results = run_cypher(query, {"flight_numbers": flight_numbers})
        print(f"✅ Expanded subgraph for {len(flight_numbers)} flights → {len(results)} enriched records")
        return results
    except Exception as e:
        print(f"❌ Error expanding subgraph: {e}")
        return []


def get_route_insights(origin: str, destination: str) -> Dict[str, Any]:
    """
    Get comprehensive insights about a specific route.
    ENHANCED: More detailed statistics.
    
    Args:
        origin: Origin airport code
        destination: Destination airport code
    
    Returns:
        Dictionary with route statistics and insights
    """
    query = """
    MATCH (j:Journey)-[:ON]->(f:Flight)
    MATCH (f)-[:DEPARTS_FROM]->(a1:Airport {station_code: $origin})
    MATCH (f)-[:ARRIVES_AT]->(a2:Airport {station_code: $destination})
    WITH f, collect(j) AS journeys
    RETURN 
        count(DISTINCT f.flight_number) AS total_flights,
        count(journeys) AS total_journeys,
        avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
        stDev([j IN journeys | j.arrival_delay_minutes]) AS delay_std_dev,
        min([j IN journeys | j.arrival_delay_minutes]) AS min_delay,
        max([j IN journeys | j.arrival_delay_minutes]) AS max_delay,
        percentileDisc([j IN journeys | j.arrival_delay_minutes], 0.5) AS median_delay,
        percentileDisc([j IN journeys | j.arrival_delay_minutes], 0.9) AS p90_delay,
        avg([j IN journeys | j.food_satisfaction_score]) AS avg_food_score,
        size([j IN journeys WHERE j.arrival_delay_minutes < 0]) AS early_arrivals,
        size([j IN journeys WHERE j.arrival_delay_minutes > 30]) AS significant_delays,
        collect(DISTINCT f.flight_number)[0..10] AS sample_flights
    """
    
    try:
        results = run_cypher(query, {"origin": origin, "destination": destination})
        if results:
            insights = results[0]
            print(f"✅ Route insights: {origin}→{destination} - {insights.get('total_flights', 0)} flights")
            return insights
        return {}
    except Exception as e:
        print(f"❌ Error getting route insights: {e}")
        return {}


def get_flight_details(flight_number: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific flight.
    ENHANCED: More comprehensive metrics.
    
    Args:
        flight_number: The flight number to query
    
    Returns:
        Dictionary with flight details
    """
    query = """
    MATCH (f:Flight {flight_number: $flight_number})
    OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(origin:Airport)
    OPTIONAL MATCH (f)-[:ARRIVES_AT]->(dest:Airport)
    OPTIONAL MATCH (j:Journey)-[:ON]->(f)
    WITH f, origin, dest, collect(j) AS journeys
    RETURN 
        f.flight_number AS flight_number,
        f.fleet_type_description AS fleet,
        origin.station_code AS origin,
        dest.station_code AS destination,
        count(journeys) AS feedback_count,
        avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
        stDev([j IN journeys | j.arrival_delay_minutes]) AS delay_consistency,
        avg([j IN journeys | j.food_satisfaction_score]) AS avg_food,
        size([j IN journeys WHERE j.food_satisfaction_score >= 4.0]) AS satisfied_passengers,
        size([j IN journeys WHERE j.food_satisfaction_score < 3.0]) AS dissatisfied_passengers
    """
    
    try:
        results = run_cypher(query, {"flight_number": flight_number})
        if results:
            print(f"✅ Flight details for {flight_number} retrieved")
            return results[0]
        print(f"⚠️  No details found for flight {flight_number}")
        return {}
    except Exception as e:
        print(f"❌ Error getting flight details: {e}")
        return {}


def search_flights_by_criteria(criteria: Dict[str, Any]) -> List[Dict]:
    """
    NEW: Flexible flight search based on multiple criteria.
    
    Args:
        criteria: Dict with optional keys:
            - min_satisfaction: Minimum satisfaction score
            - max_delay: Maximum acceptable delay
            - fleet_type: Aircraft type
            - origin/destination: Route
            - limit: Result limit
    
    Returns:
        List of matching flights
    """
    # Build dynamic query based on criteria
    conditions = []
    params = {"limit": criteria.get("limit", 10)}
    
    if "min_satisfaction" in criteria:
        conditions.append("avg(j.food_satisfaction_score) >= $min_satisfaction")
        params["min_satisfaction"] = criteria["min_satisfaction"]
    
    if "max_delay" in criteria:
        conditions.append("avg(j.arrival_delay_minutes) <= $max_delay")
        params["max_delay"] = criteria["max_delay"]
    
    where_clause = " AND ".join(conditions) if conditions else "true"
    
    query = f"""
    MATCH (j:Journey)-[:ON]->(f:Flight)
    WITH f.flight_number AS flight, collect(j) AS journeys
    WHERE size(journeys) >= 3 AND {where_clause}
    RETURN 
        flight,
        avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
        avg([j IN journeys | j.food_satisfaction_score]) AS avg_satisfaction
    ORDER BY avg_satisfaction DESC, avg_delay ASC
    LIMIT $limit
    """
    
    try:
        results = run_cypher(query, params)
        print(f"✅ Found {len(results)} flights matching criteria")
        return results
    except Exception as e:
        print(f"❌ Error in flexible search: {e}")
        return []


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Testing Enhanced Retriever ===\n")
    
    # Test 1: Intent mapping
    print("1. Testing Intent Mapping:")
    print("-" * 60)
    test_intents = [
        "flight_search", "delay_query", "complaints_search",
        "recommendation", "satisfaction_query", "unknown"
    ]
    for intent in test_intents:
        template = choose_template_for_intent(intent)
        print(f"  {intent} → {template}")
    
    # Test 2: Parameter validation
    print("\n2. Testing Parameter Validation:")
    print("-" * 60)
    test_params = {"origin": "ORD"}
    validated = validate_params(test_params, ["origin", "destination", "limit"], "find_flights_between")
    print(f"  Input: {test_params}")
    print(f"  Validated: {validated}")
    
    # Test 3: Template execution (if database available)
    print("\n3. Testing Template Execution:")
    print("-" * 60)
    try:
        results = run_template("fallback_query", {"limit": 5})
        print(f"  Fallback query returned {len(results)} results")
        if results:
            print(f"  Sample: {results[0]}")
    except Exception as e:
        print(f"  ⚠️  Database not available: {e}")
    
    print("\n✅ Enhanced retriever ready!")
    print("\nKey improvements:")
    print("  • Maps 14+ intents to templates")
    print("  • Validates and auto-fills parameters")
    print("  • Better error handling with fallbacks")
    print("  • Richer subgraph expansion")
    print("  • New flexible search function")