# backend/graph_connector.py - FIXED VERSION

import os
from neo4j import GraphDatabase, exceptions
from typing import Dict, List, Any, Optional


def load_config(path="config.txt"):
    """Load Neo4j configuration from config file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, path)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"[ERROR] Config file not found at: {config_path}")
    
    cfg = {}
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            cfg[key.strip()] = value.strip()
    
    required = ["URI", "USERNAME", "PASSWORD"]
    for r in required:
        if r not in cfg:
            raise KeyError(f"[ERROR] Missing '{r}' in config.txt")
    
    return cfg


# Load configuration
_cfg = load_config()

# Create Neo4j driver
try:
    _DRIVER = GraphDatabase.driver(
        _cfg["URI"],  
        auth=(_cfg["USERNAME"], _cfg["PASSWORD"])
    )
    
    # Test the connection
    with _DRIVER.session() as session:
        result = session.run("RETURN 1 AS test")
        result.single()
    
    print("✅ [Neo4j] Successfully connected to database!")
    
except exceptions.ServiceUnavailable as e:
    print("❌ [Neo4j ERROR] Could not connect to Neo4j. Check URI / credentials.")
    raise e
except Exception as e:
    print(f"❌ [Neo4j ERROR] Connection failed: {e}")
    raise e


def clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean and validate parameters for Neo4j queries.
    
    Neo4j is strict about:
    - No None values (use empty string or default)
    - Consistent types
    - No extra whitespace in strings
    
    Args:
        params: Raw parameters dictionary
    
    Returns:
        Cleaned parameters dictionary
    """
    cleaned = {}
    
    for key, value in params.items():
        # Handle None values
        if value is None:
            # Provide sensible defaults based on parameter name
            if key == "limit":
                cleaned[key] = 10
            elif key in ["origin", "destination", "flight_no", "fleet", "class"]:
                cleaned[key] = ""
            elif key == "min_score":
                cleaned[key] = 0.0
            else:
                cleaned[key] = ""
            print(f"⚠️  Parameter '{key}' was None, using default: {cleaned[key]}")
            continue
        
        # Clean strings
        if isinstance(value, str):
            cleaned[key] = value.strip()
        
        # Ensure limit is an integer
        elif key == "limit":
            try:
                cleaned[key] = int(value)
            except (ValueError, TypeError):
                cleaned[key] = 10
                print(f"⚠️  Invalid limit value '{value}', using default: 10")
        
        # Pass through other types
        else:
            cleaned[key] = value
    
    return cleaned


def run_cypher(query: str, params: Optional[Dict[str, Any]] = None, raise_on_error: bool = False) -> List[Dict]:
    """
    Execute a Cypher query and return results as list of dictionaries.
    
    Args:
        query: Cypher query string
        params: Query parameters dictionary
        raise_on_error: If True, raise exceptions instead of returning empty list
    
    Returns:
        List of dictionaries containing query results
    
    Raises:
        Exception: If raise_on_error=True and query fails
    """
    params = params or {}
    
    # Clean parameters
    try:
        params = clean_params(params)
    except Exception as e:
        print(f"❌ [Parameter Error] Failed to clean parameters: {e}")
        print(f"   Raw params: {params}")
        if raise_on_error:
            raise
        return []
    
    # Execute query
    try:
        with _DRIVER.session() as session:
            # Print debug info
            print(f"🔍 Executing query with params: {params}")
            
            result = session.run(query, params)
            records = [record.data() for record in result]
            
            print(f"✅ Query returned {len(records)} records")
            return records
            
    except exceptions.CypherSyntaxError as e:
        print(f"❌ [Cypher Syntax Error]")
        print(f"   Query: {query}")
        print(f"   Error: {e}")
        if raise_on_error:
            raise
        return []
    
    except exceptions.CypherTypeError as e:
        print(f"❌ [Cypher Type Error] - Parameter type mismatch")
        print(f"   Query: {query}")
        print(f"   Params: {params}")
        print(f"   Error: {e}")
        if raise_on_error:
            raise
        return []
    
    except exceptions.ConstraintError as e:
        print(f"❌ [Constraint Error]")
        print(f"   Error: {e}")
        if raise_on_error:
            raise
        return []
    
    except Exception as e:
        print(f"❌ [Query Error] Unexpected error")
        print(f"   Query: {query[:200]}...")  # First 200 chars
        print(f"   Params: {params}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error: {e}")
        if raise_on_error:
            raise
        return []


def test_connection() -> bool:
    """
    Test if Neo4j connection is working.
    
    Returns:
        True if connection works, False otherwise
    """
    try:
        result = run_cypher("RETURN 1 AS test", {}, raise_on_error=True)
        if result and result[0].get('test') == 1:
            print("✅ Connection test passed!")
            return True
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def verify_schema() -> Dict[str, Any]:
    """
    Verify that expected schema elements exist.
    
    Returns:
        Dictionary with schema verification results
    """
    results = {
        "has_flights": False,
        "has_airports": False,
        "has_journeys": False,
        "has_passengers": False,
        "issues": []
    }
    
    # Check for Flight nodes
    query = "MATCH (f:Flight) RETURN count(f) AS count LIMIT 1"
    result = run_cypher(query)
    if result and result[0].get('count', 0) > 0:
        results["has_flights"] = True
    else:
        results["issues"].append("No Flight nodes found")
    
    # Check for Airport nodes
    query = "MATCH (a:Airport) RETURN count(a) AS count LIMIT 1"
    result = run_cypher(query)
    if result and result[0].get('count', 0) > 0:
        results["has_airports"] = True
    else:
        results["issues"].append("No Airport nodes found")
    
    # Check for Journey nodes
    query = "MATCH (j:Journey) RETURN count(j) AS count LIMIT 1"
    result = run_cypher(query)
    if result and result[0].get('count', 0) > 0:
        results["has_journeys"] = True
    else:
        results["issues"].append("No Journey nodes found")
    
    # Check for Passenger nodes
    query = "MATCH (p:Passenger) RETURN count(p) AS count LIMIT 1"
    result = run_cypher(query)
    if result and result[0].get('count', 0) > 0:
        results["has_passengers"] = True
    else:
        results["issues"].append("No Passenger nodes found")
    
    return results


def get_sample_flight() -> Optional[Dict]:
    """Get a sample flight for testing."""
    query = "MATCH (f:Flight) RETURN f.flight_number AS flight_number LIMIT 1"
    result = run_cypher(query)
    if result:
        return result[0]
    return None


def get_sample_route() -> Optional[Dict]:
    """Get a sample route for testing."""
    query = """
    MATCH (f:Flight)-[:DEPARTS_FROM]->(o:Airport)
    MATCH (f)-[:ARRIVES_AT]->(d:Airport)
    RETURN o.station_code AS origin, d.station_code AS destination
    LIMIT 1
    """
    result = run_cypher(query)
    if result:
        return result[0]
    return None


# ============================================================================
# Keep your existing functions
# ============================================================================

def count_all_nodes():
    """Count total number of nodes in the database."""
    query = "MATCH (n) RETURN count(n) AS total_nodes"
    result = run_cypher(query)
    if result:
        return result[0]['total_nodes']
    return 0


def count_nodes_by_label():
    """Count nodes grouped by their labels."""
    query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
    """
    return run_cypher(query)


def count_relationships():
    """Count total number of relationships in the database."""
    query = "MATCH ()-[r]->() RETURN count(r) AS total_relationships"
    result = run_cypher(query)
    if result:
        return result[0]['total_relationships']
    return 0


def get_database_stats():
    """Get comprehensive database statistics."""
    stats = {}
    stats['total_nodes'] = count_all_nodes()
    stats['total_relationships'] = count_relationships()
    
    query = """
        CALL db.labels() YIELD label
        CALL {
            WITH label
            MATCH (n) WHERE label IN labels(n)
            RETURN count(n) AS count
        }
        RETURN label, count
        ORDER BY count DESC
    """
    result = run_cypher(query)
    stats['nodes_by_label'] = {item['label']: item['count'] for item in result}
    
    query = """
        CALL db.relationshipTypes() YIELD relationshipType
        CALL {
            WITH relationshipType
            MATCH ()-[r]->() WHERE type(r) = relationshipType
            RETURN count(r) AS count
        }
        RETURN relationshipType, count
        ORDER BY count DESC
    """
    result = run_cypher(query)
    stats['relationships_by_type'] = {item['relationshipType']: item['count'] for item in result}
    
    return stats


def print_database_summary():
    """Print a formatted summary of the database."""
    stats = get_database_stats()
    
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)
    print(f"\nTotal Nodes: {stats['total_nodes']:,}")
    print(f"Total Relationships: {stats['total_relationships']:,}")
    
    print("\n--- Nodes by Label ---")
    if stats['nodes_by_label']:
        for label, count in stats['nodes_by_label'].items():
            print(f"  {label:20s}: {count:,}")
    else:
        print("  (No nodes found)")
    
    print("\n--- Relationships by Type ---")
    if stats['relationships_by_type']:
        for rel_type, count in stats['relationships_by_type'].items():
            print(f"  {rel_type:20s}: {count:,}")
    else:
        print("  (No relationships found)")
    
    print("="*60 + "\n")


def close():
    """Close Neo4j driver connection."""
    if _DRIVER:
        _DRIVER.close()
        print("[Neo4j] Connection closed.")


# Cache node count
NODE_COUNT = count_all_nodes()


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("\n🔍 Testing Enhanced Graph Connector...\n")
    
    # Test 1: Connection
    print("1. Testing connection...")
    if test_connection():
        print("   ✅ Connection works!\n")
    else:
        print("   ❌ Connection failed!\n")
        exit(1)
    
    # Test 2: Schema verification
    print("2. Verifying schema...")
    schema_check = verify_schema()
    for key, value in schema_check.items():
        if key != "issues":
            status = "✅" if value else "❌"
            print(f"   {status} {key}: {value}")
    
    if schema_check["issues"]:
        print("\n   Issues found:")
        for issue in schema_check["issues"]:
            print(f"   ⚠️  {issue}")
    print()
    
    # Test 3: Sample data
    print("3. Getting sample data...")
    
    sample_flight = get_sample_flight()
    if sample_flight:
        print(f"   Sample flight: {sample_flight['flight_number']}")
    else:
        print("   ⚠️  No flights found")
    
    sample_route = get_sample_route()
    if sample_route:
        print(f"   Sample route: {sample_route['origin']} → {sample_route['destination']}")
    else:
        print("   ⚠️  No routes found")
    print()
    
    # Test 4: Database stats
    print("4. Database statistics:")
    print_database_summary()
    
    print("\n✅ All tests complete!")