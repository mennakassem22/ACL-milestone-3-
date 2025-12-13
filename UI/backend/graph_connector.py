# backend/graph_connector.py
from neo4j import GraphDatabase
import os

def load_config(path="config.txt"):
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, path)
    
    cfg = {}
    with open(config_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line: 
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg

_cfg = load_config()

# Rest of your code stays the same...
uri = _cfg["URI"].replace("neo4j+s://", "neo4j+ssc://")

_DRIVER = GraphDatabase.driver(
    uri, 
    auth=(_cfg["USERNAME"], _cfg["PASSWORD"])
)

def run_cypher(query: str, params: dict = None):
    params = params or {}
    with _DRIVER.session() as sess:
        res = sess.run(query, params)
        records = [r.data() for r in res]
    return records

def close():
    _DRIVER.close()