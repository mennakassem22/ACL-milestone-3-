# backend/retriever.py

from graph_connector import run_cypher
from cypher_templates import TEMPLATES
from typing import List, Dict, Any

def choose_template_for_intent(intent: str) -> str:
    """Map intent to the appropriate Cypher template."""
    mapping = {
        "flight_search": "find_flights_between",
        "delay_query": "delay_query",
        "route_stats": "avg_delay_per_route",
        "cancellation_query": "top_cancelled_routes",
        "airline_performance": "airline_performance",
        "complaints_search": "flight_complaints",
        "availability": "seat_availability",
        "connecting_flights": "connecting_flights_one_stop",
        "recommendation": "recommend_least_risky",
        "unknown": "fallback_query"
    }
    return mapping.get(intent, "fallback_query")


def run_template(template_name: str, params: Dict[str, Any]) -> List[Dict]:
    """
    Execute a Cypher query template with given parameters.
    
    Args:
        template_name: Name of the template from cypher_templates.py
        params: Dictionary of parameters to fill in the template
    
    Returns:
        List of dictionaries containing query results
    """
    if template_name not in TEMPLATES:
        print(f"Warning: Template '{template_name}' not found. Using fallback.")
        template_name = "fallback_query"
    
    template = TEMPLATES[template_name]
    cypher = template["cypher"]
    required_params = template["params"]
    
    # Fill in missing params with defaults
    for param in required_params:
        if param not in params:
            if param == "limit":
                params[param] = 10
            elif param in ["origin", "destination", "fleet", "flight_no", "class"]:
                params[param] = ""  # Will cause no matches, but won't crash
    
    try:
        results = run_cypher(cypher, params)
        return results
    except Exception as e:
        print(f"Error executing template '{template_name}': {e}")
        return []


def expand_subgraph_for_flights(flight_numbers: List[str], depth: int = 1) -> List[Dict]:
    """
    Given a list of flight numbers, retrieve a richer subgraph around them.
    This includes connected airports, journeys, passengers, etc.
    
    Args:
        flight_numbers: List of flight numbers to expand around
        depth: How many hops away from the flights to retrieve
    
    Returns:
        List of dictionaries with detailed graph information
    """
    if not flight_numbers:
        return []
    
    # Clean flight numbers (remove None/empty)
    flight_numbers = [str(fn) for fn in flight_numbers if fn]
    
    if not flight_numbers:
        return []
    
    query = """
    MATCH (f:Flight)
    WHERE f.flight_number IN $flight_numbers
    OPTIONAL MATCH (f)-[:DEPARTS_FROM]->(origin:Airport)
    OPTIONAL MATCH (f)-[:ARRIVES_AT]->(dest:Airport)
    OPTIONAL MATCH (j:Journey)-[:ON]->(f)
    WITH f, origin, dest, collect(j)[0..5] as sample_journeys
    RETURN 
        f.flight_number AS flight_number,
        f.fleet_type_description AS fleet,
        origin.station_code AS origin_code,
        origin.airport_name AS origin_name,
        dest.station_code AS dest_code,
        dest.airport_name AS dest_name,
        size(sample_journeys) AS journey_count,
        [j IN sample_journeys | {
            feedback_id: j.feedback_ID,
            arrival_delay: j.arrival_delay_minutes,
            food_score: j.food_satisfaction_score,
            inflight_entertainment_score: j.inflight_entertainment_satisfaction_score,
            seat_comfort_score: j.seat_comfort_satisfaction_score,
            passenger_class: j.passenger_class
        }] AS journeys
    """
    
    try:
        results = run_cypher(query, {"flight_numbers": flight_numbers})
        return results
    except Exception as e:
        print(f"Error expanding subgraph: {e}")
        return []


def get_route_insights(origin: str, destination: str) -> Dict[str, Any]:
    """
    Get comprehensive insights about a specific route.
    
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
    WITH f, j
    RETURN 
        count(DISTINCT f.flight_number) AS total_flights,
        count(j) AS total_journeys,
        avg(j.arrival_delay_minutes) AS avg_delay,
        stdev(j.arrival_delay_minutes) AS delay_std_dev,
        min(j.arrival_delay_minutes) AS min_delay,
        max(j.arrival_delay_minutes) AS max_delay,
        percentileDisc(j.arrival_delay_minutes, 0.5) AS median_delay,
        percentileDisc(j.arrival_delay_minutes, 0.9) AS p90_delay,
        avg(j.food_satisfaction_score) AS avg_food_score,
        avg(j.seat_comfort_satisfaction_score) AS avg_seat_comfort,
        collect(DISTINCT f.flight_number)[0..10] AS sample_flights
    """
    
    try:
        results = run_cypher(query, {"origin": origin, "destination": destination})
        return results[0] if results else {}
    except Exception as e:
        print(f"Error getting route insights: {e}")
        return {}


def get_flight_details(flight_number: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific flight.
    
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
    RETURN 
        f.flight_number AS flight_number,
        f.fleet_type_description AS fleet,
        origin.station_code AS origin,
        origin.airport_name AS origin_name,
        dest.station_code AS destination,
        dest.airport_name AS dest_name,
        count(j) AS feedback_count,
        avg(j.arrival_delay_minutes) AS avg_delay,
        avg(j.food_satisfaction_score) AS avg_food,
        avg(j.seat_comfort_satisfaction_score) AS avg_seat_comfort,
        avg(j.inflight_entertainment_satisfaction_score) AS avg_entertainment
    """
    
    try:
        results = run_cypher(query, {"flight_number": flight_number})
        return results[0] if results else {}
    except Exception as e:
        print(f"Error getting flight details: {e}")
        return {}


# Test function
if __name__ == "__main__":
    print("Testing retriever...")
    
    # Test 1: Find flights
    print("\n=== Test 1: Find flights ORD to LAX ===")
    results = run_template("find_flights_between", {
        "origin": "ORD",
        "destination": "LAX",
        "limit": 5
    })
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(r)
    
    # Test 2: Route stats
    print("\n=== Test 2: Route statistics ===")
    insights = get_route_insights("ORD", "LAX")
    print(insights)
    
    # Test 3: Expand subgraph
    if results:
        flight_nums = [r['flight_number'] for r in results[:3]]
        print(f"\n=== Test 3: Expanding subgraph for {flight_nums} ===")
        expanded = expand_subgraph_for_flights(flight_nums)
        print(f"Expanded to {len(expanded)} results")
        if expanded:
            print(expanded[0])