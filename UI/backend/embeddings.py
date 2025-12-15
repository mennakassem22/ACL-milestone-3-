# backend/embeddings.py

"""
Semantic similarity search using sentence embeddings.
Implements node embeddings for flights and routes.
"""

from sentence_transformers import SentenceTransformer
from graph_connector import run_cypher
import numpy as np
from typing import List, Dict, Tuple
import json

class EmbeddingSearch:
    """
    Handle semantic search using embeddings.
    Supports two models for comparison.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Args:
            model_name: One of:
                - "all-MiniLM-L6-v2" (fast, 384 dims)
                - "all-mpnet-base-v2" (better quality, 768 dims)
        """
        self.model_name = model_name
        print(f"Loading model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.embeddings_cache = []
        print(f"✅ Model loaded: {model_name}")
    
    def create_flight_embeddings(self, limit: int = 500) -> List[Dict]:
        """
        Create embeddings for flights by combining their properties into text.
        
        Args:
            limit: Number of flights to process
        
        Returns:
            List of dicts with flight info and embeddings
        """
        print(f"Creating embeddings for up to {limit} flights...")
        
        # Query to get flight information
        query = """
MATCH (f:Flight)-[:DEPARTS_FROM]->(origin:Airport)
MATCH (f)-[:ARRIVES_AT]->(dest:Airport)
OPTIONAL MATCH (j:Journey)-[:ON]->(f)
WITH f, origin, dest, 
     avg(j.arrival_delay_minutes) AS avg_delay,
     avg(j.food_satisfaction_score) AS avg_food,
     count(j) AS journey_count
WHERE journey_count > 0
RETURN f.flight_number AS flight_number,
       f.fleet_type_description AS fleet,
       origin.station_code AS origin_code,
       dest.station_code AS dest_code,
       avg_delay,
       avg_food,
       journey_count
LIMIT $limit
"""
        
        try:
            results = run_cypher(query, {"limit": limit})
            print(f"Retrieved {len(results)} flights from database")
        except Exception as e:
            print(f"Error querying database: {e}")
            return []
        
        embeddings_data = []
        
        for idx, record in enumerate(results):
            # Create a text description combining all features
            text = self._create_flight_description(record)
            
            # Generate embedding
            embedding = self.model.encode(text)
            
            embeddings_data.append({
                'flight_number': record['flight_number'],
                'origin': record['origin_code'],
                'destination': record['dest_code'],
                'text_description': text,
                'embedding': embedding.tolist(),
                'metadata': {
                    'fleet': record.get('fleet', 'Unknown'),
                    'avg_delay': float(record.get('avg_delay', 0)) if record.get('avg_delay') else 0,
                    'avg_food': float(record.get('avg_food', 0)) if record.get('avg_food') else 0,
                    'avg_comfort': float(record.get('avg_comfort', 0)) if record.get('avg_comfort') else 0,
                    'journey_count': record.get('journey_count', 0)
                }
            })
            
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(results)} flights...")
        
        self.embeddings_cache = embeddings_data
        print(f"✅ Created {len(embeddings_data)} embeddings")
        return embeddings_data
    
    def _create_flight_description(self, record: Dict) -> str:
        """Create a natural language description of a flight."""
        desc_parts = [
            f"Flight {record['flight_number']}",
            f"from {record['origin_name']} ({record['origin_code']})",
            f"to {record['dest_name']} ({record['dest_code']})"
        ]
        
        if record.get('fleet'):
            desc_parts.append(f"using {record['fleet']}")
        
        if record.get('avg_delay') is not None:
            delay = float(record['avg_delay'])
            if delay < 15:
                desc_parts.append("with excellent on-time performance")
            elif delay < 30:
                desc_parts.append("with good punctuality")
            else:
                desc_parts.append("with frequent delays")
        
        if record.get('avg_food') is not None:
            food = float(record['avg_food'])
            if food >= 4:
                desc_parts.append("and highly rated food service")
            elif food >= 3:
                desc_parts.append("and decent food service")
        
        return " ".join(desc_parts)
    
    def search_similar(self, query_text: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Search for flights similar to the query using semantic similarity.
        
        Args:
            query_text: Natural language query
            top_k: Number of results to return
        
        Returns:
            List of (flight_data, similarity_score) tuples
        """
        if not self.embeddings_cache:
            print("⚠️ No embeddings in cache. Creating embeddings first...")
            self.create_flight_embeddings()
        
        print(f"Searching for: '{query_text}'")
        
        # Encode query
        query_embedding = self.model.encode(query_text)
        
        # Calculate cosine similarities
        similarities = []
        for flight_data in self.embeddings_cache:
            flight_emb = np.array(flight_data['embedding'])
            
            # Cosine similarity
            similarity = np.dot(query_embedding, flight_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(flight_emb)
            )
            
            similarities.append((flight_data, float(similarity)))
        
        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        top_results = similarities[:top_k]
        
        print(f"✅ Found {len(top_results)} similar flights")
        for idx, (flight, score) in enumerate(top_results, 1):
            print(f"  {idx}. {flight['flight_number']} (score: {score:.3f})")
        
        return top_results
    
    def save_embeddings(self, filepath: str = "embeddings_cache.json"):
        """Save embeddings to file."""
        print(f"Saving embeddings to {filepath}...")
        with open(filepath, 'w') as f:
            json.dump({
                'model_name': self.model_name,
                'embeddings': self.embeddings_cache
            }, f)
        print(f"✅ Saved {len(self.embeddings_cache)} embeddings")
    
    def load_embeddings(self, filepath: str = "embeddings_cache.json"):
        """Load embeddings from file."""
        print(f"Loading embeddings from {filepath}...")
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.embeddings_cache = data['embeddings']
                print(f"✅ Loaded {len(self.embeddings_cache)} embeddings")
                return True
        except FileNotFoundError:
            print(f"⚠️ File not found: {filepath}")
            return False


# Comparison function for two models
def compare_embedding_models(query_text: str, top_k: int = 5):
    """
    Compare results from two different embedding models.
    
    Args:
        query_text: Query to test
        top_k: Number of results
    
    Returns:
        Results from both models
    """
    print("\n" + "="*80)
    print("COMPARING EMBEDDING MODELS")
    print("="*80)
    
    models = [
        "all-MiniLM-L6-v2",  # Fast, lightweight
        "all-mpnet-base-v2"   # Better quality
    ]
    
    results = {}
    
    for model_name in models:
        print(f"\n--- Testing {model_name} ---")
        searcher = EmbeddingSearch(model_name)
        searcher.create_flight_embeddings(limit=100)  # Smaller limit for testing
        
        similar_flights = searcher.search_similar(query_text, top_k)
        results[model_name] = similar_flights
    
    return results


# Test function
if __name__ == "__main__":
    print("="*80)
    print("TESTING EMBEDDING SEARCH")
    print("="*80)
    
    # Test 1: Create embeddings with Model 1
    print("\n--- Model 1: all-MiniLM-L6-v2 ---")
    searcher1 = EmbeddingSearch("all-MiniLM-L6-v2")
    searcher1.create_flight_embeddings(limit=100)
    
    # Test searches
    test_queries = [
        "flights with minimal delays",
        "comfortable long-haul flights",
        "flights from Chicago to Los Angeles",
        "reliable flights with good food"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        results = searcher1.search_similar(query, top_k=3)
        
        for idx, (flight, score) in enumerate(results, 1):
            print(f"\n{idx}. Flight {flight['flight_number']} (similarity: {score:.3f})")
            print(f"   Route: {flight['origin']} → {flight['destination']}")
            print(f"   Avg Delay: {flight['metadata']['avg_delay']:.1f} min")
            print(f"   Description: {flight['text_description'][:100]}...")
    
    # Test 2: Compare models
    print("\n\n" + "="*80)
    print("COMPARING TWO MODELS")
    print("="*80)
    
    comparison_results = compare_embedding_models(
        "Find reliable flights with minimal delays",
        top_k=3
    )
    
    print("\n Embedding search test complete!")