# backend/grounding_builder.py - ENHANCED VERSION

from typing import List, Dict, Any

def build_grounding_from_baseline(results: List[Dict[str, Any]]) -> str:
    """
    Convert graph query results into a readable text format for the LLM.
    ENHANCED: Better interpretation of delays and satisfaction scores.
    
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
                    display_value = f"[{len(value)} items]"
                    if value and isinstance(value[0], dict):
                        grounding_parts.append(f"  {key}:")
                        for item in value[:3]:  # Show first 3
                            grounding_parts.append(f"    - {item}")
                        if len(value) > 3:
                            grounding_parts.append(f"    ... and {len(value) - 3} more")
                        continue
            
            # ENHANCED: Handle delay fields specially
            elif 'delay' in key.lower() and isinstance(value, (int, float)):
                delay_value = float(value)
                if delay_value < 0:
                    display_value = f"{abs(delay_value):.1f} minutes EARLY (good performance)"
                elif delay_value == 0:
                    display_value = "On time (0 minutes)"
                else:
                    display_value = f"{delay_value:.1f} minutes LATE (poor performance)"
            
            # ENHANCED: Handle satisfaction score fields specially
            elif 'satisfaction' in key.lower() or 'score' in key.lower():
                if isinstance(value, (int, float)):
                    score = float(value)
                    if score >= 4.5:
                        display_value = f"{score:.1f}/5.0 (Excellent)"
                    elif score >= 4.0:
                        display_value = f"{score:.1f}/5.0 (Good)"
                    elif score >= 3.0:
                        display_value = f"{score:.1f}/5.0 (Average)"
                    elif score >= 2.0:
                        display_value = f"{score:.1f}/5.0 (Poor)"
                    else:
                        display_value = f"{score:.1f}/5.0 (Very Poor)"
                else:
                    display_value = str(value)
            
            # Handle regular numbers
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    display_value = f"{value:.2f}"
                else:
                    display_value = str(value)
            
            # Handle everything else
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
                    # Apply same enhancements for delays and scores
                    if 'delay' in key.lower() and isinstance(value, (int, float)):
                        delay_value = float(value)
                        if delay_value < 0:
                            display_value = f"{abs(delay_value):.1f} min EARLY"
                        else:
                            display_value = f"{delay_value:.1f} min LATE"
                    elif 'satisfaction' in key.lower() or 'score' in key.lower():
                        if isinstance(value, (int, float)):
                            display_value = f"{float(value):.1f}/5.0"
                        else:
                            display_value = str(value)
                    else:
                        display_value = str(value)
                    
                    parts.append(f"  {key}: {display_value}")
            parts.append("")
    
    return "".join(parts)


def format_for_recommendation(results: List[Dict[str, Any]], 
                              ranking_key: str = "avg_delay") -> str:
    """
    Format results specifically for recommendation tasks.
    Sorts and highlights the best options.
    ENHANCED: Better interpretation of what "best" means.
    
    Args:
        results: Query results to format
        ranking_key: Key to use for ranking
    
    Returns:
        Formatted recommendation text
    """
    if not results:
        return "No recommendations available based on current data."
    
    # Sort results - SMART SORTING
    # For delays: negative (early) is better, so sort ascending
    if 'delay' in ranking_key.lower():
        sorted_results = sorted(results, key=lambda x: x.get(ranking_key, float('inf')))
    else:
        # For scores: higher is better, so sort descending
        sorted_results = sorted(results, key=lambda x: x.get(ranking_key, 0), reverse=True)
    
    parts = []
    parts.append("=== RANKED RECOMMENDATIONS ===\n")
    parts.append("Flights ranked from BEST to WORST:\n")
    
    for idx, record in enumerate(sorted_results[:10], 1):  # Top 10
        if idx == 1:
            parts.append(f"🥇 Rank #{idx} - BEST CHOICE:")
        elif idx == 2:
            parts.append(f"🥈 Rank #{idx} - SECOND BEST:")
        elif idx == 3:
            parts.append(f"🥉 Rank #{idx} - THIRD BEST:")
        else:
            parts.append(f"Rank #{idx}:")
        
        # Highlight key info
        if "flight_number" in record:
            parts.append(f"  Flight: {record['flight_number']}")
        
        # Show ranking metric with interpretation
        if ranking_key in record:
            value = record[ranking_key]
            if 'delay' in ranking_key.lower() and isinstance(value, (int, float)):
                delay = float(value)
                if delay < 0:
                    parts.append(f"  ✅ Arrival: {abs(delay):.1f} min EARLY (excellent)")
                elif delay < 15:
                    parts.append(f"  ⚠️  Arrival: {delay:.1f} min late (acceptable)")
                else:
                    parts.append(f"  ❌ Arrival: {delay:.1f} min LATE (poor)")
            else:
                parts.append(f"  {ranking_key}: {value}")
        
        # Add other relevant info
        for key, value in record.items():
            if key not in ["flight_number", ranking_key] and value is not None:
                if 'satisfaction' in key.lower() or 'score' in key.lower():
                    if isinstance(value, (int, float)):
                        score = float(value)
                        if score >= 4.0:
                            parts.append(f"  ✅ {key}: {score:.1f}/5.0 (good)")
                        elif score >= 3.0:
                            parts.append(f"  ⚠️  {key}: {score:.1f}/5.0 (average)")
                        else:
                            parts.append(f"  ❌ {key}: {score:.1f}/5.0 (poor)")
                    else:
                        parts.append(f"  {key}: {value}")
                elif isinstance(value, float):
                    parts.append(f"  {key}: {value:.2f}")
                else:
                    parts.append(f"  {key}: {value}")
        
        parts.append("")
    
    return "\n".join(parts)


def summarize_data_quality(results: List[Dict[str, Any]]) -> str:
    """
    NEW: Provide a quick summary of the data quality and completeness.
    
    Args:
        results: Query results
    
    Returns:
        Data quality summary
    """
    if not results:
        return "No data available."
    
    summary = []
    summary.append("=== DATA QUALITY SUMMARY ===")
    summary.append(f"Total records: {len(results)}")
    
    # Check for key fields
    has_delays = any('delay' in str(k).lower() for r in results for k in r.keys())
    has_satisfaction = any('satisfaction' in str(k).lower() or 'score' in str(k).lower() for r in results for k in r.keys())
    has_flights = any('flight' in str(k).lower() for r in results for k in r.keys())
    
    summary.append(f"Contains delay data: {'Yes' if has_delays else 'No'}")
    summary.append(f"Contains satisfaction data: {'Yes' if has_satisfaction else 'No'}")
    summary.append(f"Contains flight identifiers: {'Yes' if has_flights else 'No'}")
    
    return "\n".join(summary)


# Test function
if __name__ == "__main__":
    # Sample test data
    test_results = [
        {
            "flight_number": "1004",
            "passenger": "LHXX2P",
            "feedback_id": "F_2778",
            "food_satisfaction_score": 5.0,
            "seat_comfort_satisfaction_score": 4.5,
            "arrival_delay_minutes": -18.0,
            "number_of_legs": 1
        },
        {
            "flight_number": "1005",
            "avg_arrival_delay": 45.2,
            "avg_food_score": 2.5,
            "feedback_count": 156
        }
    ]
    
    print("=== Testing Enhanced Grounding Builder ===\n")
    
    print("1. Basic Grounding (with enhancements):")
    print("-" * 80)
    grounding = build_grounding_from_baseline(test_results)
    print(grounding)
    
    print("\n2. Provenance Table:")
    print("-" * 80)
    print(build_provenance_table(test_results))
    
    print("\n3. Recommendation Format:")
    print("-" * 80)
    print(format_for_recommendation(test_results, "arrival_delay_minutes"))
    
    print("\n4. Data Quality Summary:")
    print("-" * 80)
    print(summarize_data_quality(test_results))
    
    print("\n✅ Key Enhancements:")
    print("  • Delays show as 'EARLY (good)' or 'LATE (poor)'")
    print("  • Satisfaction scores show scale and quality")
    print("  • Recommendations show best to worst")
    print("  • Visual indicators (✅ ⚠️ ❌) for quick scanning")