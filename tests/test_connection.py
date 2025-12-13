from graph_connector import run_cypher
import traceback

try:
    result = run_cypher("MATCH (n) RETURN count(n) AS count")
    print("Connection successful!")
    print("Node count:", result)
except Exception as e:
    print("Connection failed.")
    print("Error type:", type(e).__name__)
    print("Error message:", str(e))
    print("\nFull traceback:")
    traceback.print_exc()