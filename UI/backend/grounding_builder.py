# backend/grounding_builder.py

from typing import List, Dict, Any

def build_grounding_from_baseline(results: List[Dict[str, Any]]) -> str:
    """
    Convert graph query results into a readable text format for the LLM.
    This creates the 'context' part of the prompt.
    
    Args:
        results: List of dictionaries from Neo4j query results
    
    Returns:
        Formatted string with graph information
    """
    if not results:
        return "No relevant data found in the knowledge graph."
    
    grounding_parts = []
    grounding_parts.append("=== KNOWLEDGE GRAPH INFORMATION ===\n")
    
    for idx, record in enumerate(results, 1):
        grounding_parts.append(f"Record {idx}:")
        
        for key, value in record.items():
            # Handle None values
            if value is None:
                display_value = "N/A"
            # Handle lists (like journeys)
            elif isinstance(value, list):
                if len(value) == 0:
                    display_value = "[]"
                else:
                    # Pretty print first few items
                    display_value = f"[{len(value)} items]"
                    # Show sample if items are dicts
                    if value and isinstance(value[0], dict):
                        grounding_parts.append(f"  {key}:")
                        for item in value[:3]:  # Show first 3
                            grounding_parts.append(f"    - {item}")
                        if len(value) > 3:
                            grounding_parts.append(f"    ... and {len(value) - 3} more")
                        continue
            # Handle numbers
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    display_value = f"{value:.2f}"
                else:
                    display_value = str(value)
            else:
                display_value = str(value)
            
            grounding_parts.append(f"  {key}: {display_value}")
        
        grounding_parts.append("")  # Empty line between records
    
    return "\n".join(grounding_parts)


def build_provenance_table(results: List[Dict[str, Any]]) -> str:
    """
    Create a provenance table showing the source of each fact.
    This helps with transparency and trust.
    
    Args:
        results: List of dictionaries from Neo4j query results
    
    Returns:
        Formatted provenance table
    """
    if not results:
        return "No provenance information available."
    
    provenance = []
    provenance.append("=== DATA PROVENANCE ===")
    provenance.append("All information retrieved from Neo4j Knowledge Graph:")
    provenance.append("")
    
    # Extract entity types and counts
    entity_types = set()
    for record in results:
        for key in record.keys():
            # Try to identify entity types from key names
            if "flight" in key.lower():
                entity_types.add("Flights")
            elif "airport" in key.lower() or "origin" in key.lower() or "dest" in key.lower():
                entity_types.add("Airports")
            elif "journey" in key.lower() or "feedback" in key.lower():
                entity_types.add("Journeys")
            elif "passenger" in key.lower():
                entity_types.add("Passengers")
    
    provenance.append(f"Total records retrieved: {len(results)}")
    if entity_types:
        provenance.append(f"Entity types involved: {', '.join(sorted(entity_types))}")
    provenance.append("")
    
    # Add sample entity IDs for verification
    provenance.append("Sample entity identifiers:")
    for record in results[:5]:  # First 5 records
        identifiers = []
        for key, value in record.items():
            if key in ["flight_number", "flight", "origin", "destination", "feedback_id"]:
                if value:
                    identifiers.append(f"{key}={value}")
        if identifiers:
            provenance.append(f"  - {', '.join(identifiers)}")
    
    return "\n".join(provenance)


def build_grounding_with_embeddings(baseline_results: List[Dict], 
                                   embedding_results: List[Dict],
                                   embedding_scores: List[float] = None) -> str:
    """
    Combine baseline and embedding-based retrieval results.
    
    Args:
        baseline_results: Results from Cypher queries
        embedding_results: Results from similarity search
        embedding_scores: Optional similarity scores for embedding results
    
    Returns:
        Combined grounding text
    """
    parts = []
    
    # Baseline results
    if baseline_results:
        parts.append("=== EXACT MATCH RESULTS (Cypher Queries) ===\n")
        parts.append(build_grounding_from_baseline(baseline_results))
        parts.append("\n")
    
    # Embedding results
    if embedding_results:
        parts.append("=== SEMANTICALLY SIMILAR RESULTS (Embeddings) ===\n")
        for idx, (record, score) in enumerate(zip(embedding_results, embedding_scores or [0] * len(embedding_results)), 1):
            parts.append(f"Match {idx} (similarity: {score:.3f}):")
            for key, value in record.items():
                if value is not None:
                    parts.append(f"  {key}: {value}")
            parts.append("")
    
    return "".join(parts)


def format_for_recommendation(results: List[Dict[str, Any]], 
                              ranking_key: str = "avg_delay") -> str:
    """
    Format results specifically for recommendation tasks.
    Sorts and highlights the best options.
    
    Args:
        results: Query results to format
        ranking_key: Key to use for ranking (lower is better for delays)
    
    Returns:
        Formatted recommendation text
    """
    if not results:
        return "No recommendations available based on current data."
    
    # Sort results
    sorted_results = sorted(results, key=lambda x: x.get(ranking_key, float('inf')))
    
    parts = []
    parts.append("=== RANKED RECOMMENDATIONS ===\n")
    
    for idx, record in enumerate(sorted_results[:10], 1):  # Top 10
        parts.append(f"Rank #{idx}:")
        
        # Highlight key metrics
        if "flight_number" in record:
            parts.append(f"  Flight: {record['flight_number']}")
        if ranking_key in record:
            parts.append(f"  {ranking_key}: {record[ranking_key]}")
        
        # Add other relevant info
        for key, value in record.items():
            if key not in ["flight_number", ranking_key] and value is not None:
                if isinstance(value, float):
                    parts.append(f"  {key}: {value:.2f}")
                else:
                    parts.append(f"  {key}: {value}")
        
        parts.append("")
    
    return "\n".join(parts)


# Test function
if __name__ == "__main__":
    # Sample test data
    test_results = [
        {
            "flight_number": "UA123",
            "fleet": "Boeing 737",
            "avg_arrival_delay": 45.2,
            "feedback_count": 156
        },
        {
            "flight_number": "AA456",
            "fleet": "Airbus A320",
            "avg_arrival_delay": 12.5,
            "feedback_count": 203
        }
    ]
    
    print("=== Testing Grounding Builder ===\n")
    
    print("1. Basic Grounding:")
    print(build_grounding_from_baseline(test_results))
    
    print("\n2. Provenance Table:")
    print(build_provenance_table(test_results))
    
    print("\n3. Recommendation Format:")
    print(format_for_recommendation(test_results, "avg_arrival_delay"))