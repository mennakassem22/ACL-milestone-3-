# backend/graph_connector.py
import os
from neo4j import GraphDatabase, exceptions


def load_config(path="config.txt"):
    """Load Neo4j configuration from config file."""
    # Determine absolute path to config file
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
    
    # Validate required fields
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
    print("[Neo4j] Successfully connected to database!")
    
except exceptions.ServiceUnavailable as e:
    print("[Neo4j ERROR] Could not connect to Neo4j. Check URI / credentials.")
    raise e


def run_cypher(query: str, params: dict = None):
    """Executes a Cypher query and returns the results as a list of dictionaries."""
    params = params or {}
    try:
        with _DRIVER.session() as session:
            result = session.run(query, params)
            return [record.data() for record in result]
    except Exception as e:
        print(f"[Cypher ERROR] Query failed:\n{query}\nParams: {params}\n{e}")
        return []


# ============================================================================
# NODE COUNTING FUNCTIONS
# ============================================================================

def count_all_nodes():
    """
    Count total number of nodes in the database.
    
    Returns:
        int: Total number of nodes
    """
    query = "MATCH (n) RETURN count(n) AS total_nodes"
    result = run_cypher(query)
    if result:
        return result[0]['total_nodes']
    return 0
    print()


def count_nodes_by_label():
    """
    Count nodes grouped by their labels.
    
    Returns:
        list: List of dictionaries with 'label' and 'count' keys
    """
    query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, count(n) AS count
        ORDER BY count DESC
    """
    return run_cypher(query)


def count_relationships():
    """
    Count total number of relationships in the database.
    
    Returns:
        int: Total number of relationships
    """
    query = "MATCH ()-[r]->() RETURN count(r) AS total_relationships"
    result = run_cypher(query)
    if result:
        return result[0]['total_relationships']
    return 0


def get_database_stats():
    """
    Get comprehensive database statistics.
    
    Returns:
        dict: Dictionary containing:
            - total_nodes: int
            - total_relationships: int
            - nodes_by_label: dict {label: count}
            - relationships_by_type: dict {type: count}
    """
    stats = {}
    
    # Total nodes
    stats['total_nodes'] = count_all_nodes()
    
    # Total relationships
    stats['total_relationships'] = count_relationships()
    
    # Nodes by label
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
    
    # Relationships by type
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


# ============================================================================
# SCHEMA INSPECTION FUNCTIONS
# ============================================================================

def get_schema_info():
    """
    Get database schema information (labels, relationship types, properties).
    
    Returns:
        dict: Schema information
    """
    schema = {}
    
    # Get all labels
    query = "CALL db.labels()"
    result = run_cypher(query)
    schema['labels'] = [record['label'] for record in result]
    
    # Get all relationship types
    query = "CALL db.relationshipTypes()"
    result = run_cypher(query)
    schema['relationship_types'] = [record['relationshipType'] for record in result]
    
    # Get property keys
    query = "CALL db.propertyKeys()"
    result = run_cypher(query)
    schema['property_keys'] = [record['propertyKey'] for record in result]
    
    return schema


def inspect_node_properties(label: str, limit: int = 1):
    """
    Inspect properties of nodes with a specific label.
    
    Args:
        label: Node label to inspect
        limit: Number of sample nodes to return
    
    Returns:
        list: Sample nodes with their properties
    """
    query = f"MATCH (n:{label}) RETURN properties(n) AS props LIMIT $limit"
    result = run_cypher(query, {"limit": limit})
    return result


def print_schema_summary():
    """Print a formatted summary of the database schema."""
    schema = get_schema_info()
    
    print("\n" + "="*60)
    print("SCHEMA SUMMARY")
    print("="*60)
    
    print("\n--- Node Labels ---")
    if schema['labels']:
        for label in schema['labels']:
            print(f"  - {label}")
    else:
        print("  (No labels found)")
    
    print("\n--- Relationship Types ---")
    if schema['relationship_types']:
        for rel_type in schema['relationship_types']:
            print(f"  - {rel_type}")
    else:
        print("  (No relationship types found)")
    
    print("\n--- Property Keys ---")
    if schema['property_keys']:
        for prop in schema['property_keys']:
            print(f"  - {prop}")
    else:
        print("  (No properties found)")
    
    print("="*60 + "\n")


def close():
    """Close Neo4j driver connection."""
    if _DRIVER:
        _DRIVER.close()
        print("[Neo4j] Connection closed.")


# ============================================================================
# CONVENIENCE VARIABLE FOR QUICK ACCESS
# ============================================================================

# Get node count when module is imported (cached)
NODE_COUNT = count_all_nodes()


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "_main_":
    # Test the functions
    print("\n🔍 Testing Database Statistics...")
    
    # Quick node count
    print(f"\nQuick access: NODE_COUNT = {NODE_COUNT}")
    
    # Detailed stats
    print_database_summary()
    
    # Schema info
    print_schema_summary()
    
    # Sample nodes for each label
    schema = get_schema_info()
    if schema['labels']:
        print("\n--- Sample Node Properties ---")
        for label in schema['labels'][:3]:  # First 3 labels
            print(f"\n{label} (sample):")
            samples = inspect_node_properties(label, limit=1)
            for sample in samples:
                for key, value in sample['props'].items():
                    print(f"  {key}: {value}")
    
    # Close connection
    close()