# backend/cypher_templates.py - ENHANCED VERSION

TEMPLATES = {

    # =========================================================================
    # FLIGHT SEARCH QUERIES
    # =========================================================================

    # 1) Find flights between airports with comprehensive stats
    "find_flights_between": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
WITH f, 
     f.flight_number AS flight_number,
     f.fleet_type_description AS fleet,
     collect(j) AS journeys
RETURN DISTINCT 
    flight_number, 
    fleet,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_arrival_delay,
    avg([j IN journeys | j.food_satisfaction_score]) AS avg_food_score,
    count(journeys) AS feedback_count,
    min([j IN journeys | j.arrival_delay_minutes]) AS min_delay,
    max([j IN journeys | j.arrival_delay_minutes]) AS max_delay
ORDER BY avg_arrival_delay ASC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    # =========================================================================
    # DELAY ANALYSIS QUERIES
    # =========================================================================

    # 2) Detailed delay statistics with percentiles
    "delay_query": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
WITH f.flight_number AS flight_number, 
     f.fleet_type_description AS fleet,
     collect(j.arrival_delay_minutes) AS delays
RETURN 
    flight_number,
    fleet,
    avg(delays) AS avg_delay,
    stDev(delays) AS delay_std_dev,
    min(delays) AS min_delay,
    max(delays) AS max_delay,
    percentileDisc(delays, 0.5) AS median_delay,
    percentileDisc(delays, 0.9) AS p90_delay,
    size(delays) AS sample_count
ORDER BY avg_delay DESC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    # 3) Average delay per route with route stats
    "avg_delay_per_route": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WITH 
    a1.station_code AS origin, 
    a2.station_code AS destination,
    collect(j.arrival_delay_minutes) AS all_delays,
    count(DISTINCT f) AS unique_flights,
    count(j) AS total_journeys
RETURN 
    origin, 
    destination, 
    avg(all_delays) AS avg_delay,
    stDev(all_delays) AS delay_variation,
    unique_flights,
    total_journeys,
    percentileDisc(all_delays, 0.9) AS p90_delay
ORDER BY avg_delay DESC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    # =========================================================================
    # CANCELLATION & RELIABILITY QUERIES
    # =========================================================================

    # 4) Routes with severe delays (proxy for cancellations)
    "top_cancelled_routes": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE j.arrival_delay_minutes > 180
WITH 
    a1.station_code AS origin, 
    a2.station_code AS destination,
    count(j) AS severe_delays,
    avg(j.arrival_delay_minutes) AS avg_severe_delay
RETURN 
    origin, 
    destination,
    severe_delays AS problematic_flights,
    avg_severe_delay
ORDER BY severe_delays DESC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    # =========================================================================
    # AIRLINE/FLEET PERFORMANCE QUERIES
    # =========================================================================

    # 5) Comprehensive airline/fleet performance
    "airline_performance": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.fleet_type_description = $fleet
WITH f.fleet_type_description AS fleet,
     collect(j) AS journeys
RETURN 
    fleet,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
    stDev([j IN journeys | j.arrival_delay_minutes]) AS delay_std_dev,
    avg([j IN journeys | j.food_satisfaction_score]) AS avg_food_score,
    count(journeys) AS total_flights,
    size([j IN journeys WHERE j.arrival_delay_minutes > 30]) AS significantly_delayed
ORDER BY avg_delay ASC;
""",
        "params": ["fleet"]
    },

    # =========================================================================
    # FEEDBACK & COMPLAINTS QUERIES
    # =========================================================================

    # 6) Comprehensive flight feedback with satisfaction breakdown
    "flight_complaints": {
        "cypher": """
MATCH (p:Passenger)-[t:TOOK]->(j:Journey)-[:ON]->(f:Flight)
WHERE f.flight_number = $flight_no
RETURN 
    p.record_locator AS passenger,
    j.feedback_ID AS feedback_id,
    j.food_satisfaction_score AS food_score,
    j.arrival_delay_minutes AS delay,
    j.number_of_legs AS legs,
    j.passenger_class AS travel_class
ORDER BY j.feedback_ID DESC
LIMIT $limit;
""",
        "params": ["flight_no", "limit"]
    },

    # NEW: Get overall satisfaction statistics for a flight
    "flight_satisfaction_stats": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.flight_number = $flight_no
WITH f.flight_number AS flight,
     collect(j) AS journeys
RETURN 
    flight,
    avg([j IN journeys | j.food_satisfaction_score]) AS avg_food,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
    count(journeys) AS total_feedback,
    size([j IN journeys WHERE j.food_satisfaction_score < 3.0]) AS poor_ratings,
    size([j IN journeys WHERE j.food_satisfaction_score >= 4.0]) AS good_ratings
""",
        "params": ["flight_no"]
    },

    # =========================================================================
    # SEAT & CAPACITY QUERIES
    # =========================================================================

    # 7) Passenger class distribution for flights
    "seat_availability": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.flight_number = $flight_no 
  AND (j.passenger_class = $class OR $class = '')
WITH f.flight_number AS flight,
     j.passenger_class AS class,
     count(j) AS passengers
RETURN 
    flight, 
    class,
    passengers
ORDER BY passengers DESC;
""",
        "params": ["flight_no", "class"]
    },

    # =========================================================================
    # CONNECTION & ROUTING QUERIES
    # =========================================================================

    # 8) One-stop connections with timing info
    "connecting_flights_one_stop": {
        "cypher": """
MATCH (f1:Flight)-[:DEPARTS_FROM]->(orig:Airport)
MATCH (f1)-[:ARRIVES_AT]->(mid:Airport)
MATCH (f2:Flight)-[:DEPARTS_FROM]->(mid)
MATCH (f2)-[:ARRIVES_AT]->(dest:Airport)
WHERE orig.station_code = $origin
  AND dest.station_code = $destination
  AND f1.flight_number <> f2.flight_number
OPTIONAL MATCH (j1:Journey)-[:ON]->(f1)
OPTIONAL MATCH (j2:Journey)-[:ON]->(f2)
WITH f1, f2, mid,
     avg(j1.arrival_delay_minutes) AS leg1_delay,
     avg(j2.arrival_delay_minutes) AS leg2_delay
RETURN 
    f1.flight_number AS leg1,
    mid.station_code AS through,
    f2.flight_number AS leg2,
    leg1_delay,
    leg2_delay,
    (leg1_delay + leg2_delay) AS total_expected_delay
ORDER BY total_expected_delay ASC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    # =========================================================================
    # RECOMMENDATION QUERIES
    # =========================================================================

    # 9) Comprehensive flight recommendation
    "recommend_least_risky": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
WITH f.flight_number AS flight,
     f.fleet_type_description AS fleet,
     collect(j) AS journeys
WITH flight, fleet,
     avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
     stDev([j IN journeys | j.arrival_delay_minutes]) AS delay_consistency,
     avg([j IN journeys | j.food_satisfaction_score]) AS avg_satisfaction,
     count(journeys) AS reliability_score
WHERE reliability_score >= 3
RETURN 
    flight, 
    fleet,
    avg_delay,
    delay_consistency,
    avg_satisfaction,
    reliability_score,
    (avg_delay * 0.4 + delay_consistency * 0.2 - avg_satisfaction * 2) AS risk_score
ORDER BY risk_score ASC, reliability_score DESC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    # NEW: Best overall flights (no route restriction)
    "recommend_best_flights": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WITH f.flight_number AS flight,
     collect(j) AS journeys
WHERE size(journeys) >= 5
WITH flight,
     avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
     avg([j IN journeys | j.food_satisfaction_score]) AS avg_satisfaction,
     count(journeys) AS sample_size
RETURN 
    flight,
    avg_delay,
    avg_satisfaction,
    sample_size,
    (5 - avg_satisfaction) * 10 + avg_delay AS quality_score
ORDER BY quality_score ASC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    # =========================================================================
    # GENERAL SEARCH QUERIES
    # =========================================================================

    # 10) Enhanced fallback with basic stats
    "fallback_query": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WITH f.flight_number AS flight,
     avg(j.arrival_delay_minutes) AS avg_delay,
     count(j) AS feedback_count
WHERE feedback_count >= 1
RETURN DISTINCT 
    flight AS flight_number,
    avg_delay,
    feedback_count
ORDER BY feedback_count DESC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    # NEW: Search flights by fleet type
    "search_by_fleet": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE toLower(f.fleet_type_description) CONTAINS toLower($fleet)
WITH f.flight_number AS flight,
     f.fleet_type_description AS fleet_type,
     collect(j) AS journeys
RETURN 
    flight,
    fleet_type,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
    count(journeys) AS flights_count
ORDER BY avg_delay ASC
LIMIT $limit;
""",
        "params": ["fleet", "limit"]
    },

    # NEW: Find flights with specific satisfaction criteria
    "search_high_satisfaction": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE j.food_satisfaction_score >= $min_score
WITH f.flight_number AS flight,
     f.fleet_type_description AS fleet,
     collect(j) AS journeys
WHERE size(journeys) >= 3
RETURN 
    flight,
    fleet,
    avg([j IN journeys | j.food_satisfaction_score]) AS avg_satisfaction,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
    count(journeys) AS sample_size
ORDER BY avg_satisfaction DESC, avg_delay ASC
LIMIT $limit;
""",
        "params": ["min_score", "limit"]
    },

    # NEW: Route comparison query
    "compare_routes": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(origin:Airport)
MATCH (f)-[:ARRIVES_AT]->(dest:Airport)
WITH origin.station_code AS origin_code,
     dest.station_code AS dest_code,
     collect(j) AS journeys,
     count(DISTINCT f) AS flight_options
RETURN 
    origin_code,
    dest_code,
    flight_options,
    avg([j IN journeys | j.arrival_delay_minutes]) AS avg_delay,
    avg([j IN journeys | j.food_satisfaction_score]) AS avg_satisfaction,
    count(journeys) AS total_journeys
ORDER BY avg_satisfaction DESC, avg_delay ASC
LIMIT $limit;
""",
        "params": ["limit"]
    }

}

# ============================================================================
# QUERY METADATA - Helpful descriptions for each template
# ============================================================================

QUERY_DESCRIPTIONS = {
    "find_flights_between": "Find flights between two airports with delay and satisfaction stats",
    "delay_query": "Detailed delay analysis with percentiles and statistics",
    "avg_delay_per_route": "Average delays aggregated by route",
    "top_cancelled_routes": "Routes with highest number of severe delays",
    "airline_performance": "Performance metrics for specific fleet types",
    "flight_complaints": "Passenger feedback for a specific flight",
    "flight_satisfaction_stats": "Overall satisfaction statistics for a flight",
    "seat_availability": "Passenger distribution by class for a flight",
    "connecting_flights_one_stop": "One-stop connection options with timing",
    "recommend_least_risky": "Recommended flights based on reliability",
    "recommend_best_flights": "Best overall flights across all routes",
    "fallback_query": "General flight listing with basic stats",
    "search_by_fleet": "Search flights by aircraft type",
    "search_high_satisfaction": "Find flights with high passenger satisfaction",
    "compare_routes": "Compare performance across different routes"
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_template(template_name: str) -> dict:
    """
    Get a query template by name.
    
    Args:
        template_name: Name of the template
    
    Returns:
        Template dict with cypher and params
    """
    return TEMPLATES.get(template_name, TEMPLATES["fallback_query"])


def list_available_templates() -> list:
    """Get list of all available template names."""
    return list(TEMPLATES.keys())


def get_template_description(template_name: str) -> str:
    """Get human-readable description of what a template does."""
    return QUERY_DESCRIPTIONS.get(template_name, "No description available")


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=== Available Cypher Query Templates ===\n")
    
    for idx, (name, desc) in enumerate(QUERY_DESCRIPTIONS.items(), 1):
        print(f"{idx}. {name}")
        print(f"   {desc}")
        print(f"   Parameters: {TEMPLATES[name]['params']}")
        print()
    
    print(f"\n✅ Total templates: {len(TEMPLATES)}")
    print(f"✅ Enhanced with better aggregations and statistics")
    print(f"✅ Includes {len(TEMPLATES) - 10} new query types")