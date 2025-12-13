# backend/cypher_templates.py

TEMPLATES = {
    "find_flights_between": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
RETURN DISTINCT f.flight_number AS flight_number, f.fleet_type_description AS fleet, 
       avg(j.arrival_delay_minutes) AS avg_arrival_delay, count(j) AS feedback_count
ORDER BY avg_arrival_delay DESC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    "delay_query": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
RETURN f.flight_number AS flight_number, avg(j.arrival_delay_minutes) AS avg_delay, percentileDisc(collect(j.arrival_delay_minutes), 0.9) AS p90
ORDER BY avg_delay DESC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    "avg_delay_per_route": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WITH a1.station_code AS origin, a2.station_code AS destination, avg(j.arrival_delay_minutes) AS avgDelay, count(*) AS flights
RETURN origin, destination, avgDelay, flights
ORDER BY avgDelay DESC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    "top_cancelled_routes": {
        # If you don't have explicit cancellation flags, skip or adapt. Placeholder:
        "cypher": """
// If cancellations are modeled, replace this with correct property
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.status = 'cancelled'
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
RETURN a1.station_code AS origin, a2.station_code AS destination, count(f) AS cancelledCount
ORDER BY cancelledCount DESC
LIMIT $limit;
""",
        "params": ["limit"]
    },

    "airline_performance": {
        "cypher": """
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.fleet_type_description = $fleet
RETURN f.fleet_type_description AS fleet, avg(j.arrival_delay_minutes) AS avgDelay, count(j) AS feedbackCount;
""",
        "params": ["fleet"]
    },

    "flight_complaints": {
        "cypher": """
MATCH (p:Passenger)-[t:TOOK]->(j:Journey)-[:ON]->(f:Flight)
WHERE f.flight_number = $flight_no
RETURN p.record_locator AS passenger, j.feedback_ID AS feedback_id, j.food_satisfaction_score AS food_score,
       j.arrival_delay_minutes AS delay, j.number_of_legs AS legs
ORDER BY j.feedback_ID DESC
LIMIT $limit;
""",
        "params": ["flight_no", "limit"]
    },

    "seat_availability": {
        "cypher": """
// If seat availability exists in schema. If not, adapt to your dataset.
MATCH (j:Journey)-[:ON]->(f:Flight)
WHERE f.flight_number = $flight_no AND j.passenger_class = $class
RETURN f.flight_number AS flight_no, count(j) AS booked_count;
""",
        "params": ["flight_no", "class"]
    },

    "connecting_flights_one_stop": {
        "cypher": """
MATCH (j1:Journey)-[:ON]->(f1:Flight)-[:ARRIVES_AT]->(mid:Airport),
      (f2:Flight)-[:DEPARTS_FROM]->(mid)-[:DEPARTS_FROM]->(mid) 
// above line is placeholder — we'll do a different approach below
WITH f1, mid
MATCH (f2:Flight)-[:DEPARTS_FROM]->(mid)-[:ARRIVES_AT]->(dest:Airport)
WHERE f1.flight_number <> f2.flight_number
RETURN f1.flight_number AS leg1, mid.station_code AS via, f2.flight_number AS leg2
LIMIT $limit;
""",
        "params": ["limit"]
    },

    "recommend_least_risky": {
        "cypher": """
// a simple heuristic: low avg delay + high feedback_count
MATCH (j:Journey)-[:ON]->(f:Flight)
MATCH (f)-[:DEPARTS_FROM]->(a1:Airport)
MATCH (f)-[:ARRIVES_AT]->(a2:Airport)
WHERE a1.station_code = $origin AND a2.station_code = $destination
WITH f.flight_number AS flight, avg(j.arrival_delay_minutes) AS avgDelay, count(j) AS feedbackCount
RETURN flight, avgDelay, feedbackCount
ORDER BY avgDelay ASC, feedbackCount DESC
LIMIT $limit;
""",
        "params": ["origin", "destination", "limit"]
    },

    "fallback_query": {
        "cypher": "MATCH (f:Flight) RETURN DISTINCT f.flight_number AS flight_number LIMIT $limit;",
        "params": ["limit"]
    }
}
