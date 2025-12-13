# backend/llm_prompt.py

from typing import Optional

def build_prompt(user_query: str, 
                grounding_context: str, 
                provenance: Optional[str] = None,
                task_type: str = "qa") -> str:
    """
    Build a structured prompt with context, persona, and task.
    
    Args:
        user_query: The original user question
        grounding_context: The formatted graph data (from grounding_builder)
        provenance: Optional provenance information
        task_type: Type of task ("qa", "recommendation", "booking")
    
    Returns:
        Complete prompt string for the LLM
    """
    
    # Define persona based on task type
    personas = {
        "qa": "You are an expert airline data analyst with access to a comprehensive flight database.",
        "recommendation": "You are a helpful flight recommendation assistant for airline operations.",
        "booking": "You are a professional travel booking assistant.",
        "insights": "You are a senior airline operations analyst providing actionable insights."
    }
    
    persona = personas.get(task_type, personas["qa"])
    
    # Build the structured prompt
    prompt_parts = []
    
    # 1. PERSONA
    prompt_parts.append(f"=== YOUR ROLE ===")
    prompt_parts.append(persona)
    prompt_parts.append("")
    
    # 2. CONTEXT (the graph data)
    prompt_parts.append(f"=== AVAILABLE DATA ===")
    prompt_parts.append(grounding_context)
    prompt_parts.append("")
    
    # 3. PROVENANCE (if provided)
    if provenance:
        prompt_parts.append(provenance)
        prompt_parts.append("")
    
    # 4. TASK INSTRUCTIONS
    prompt_parts.append(f"=== YOUR TASK ===")
    
    if task_type == "qa":
        prompt_parts.append("Answer the user's question using ONLY the information provided above.")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- Be precise and factual")
        prompt_parts.append("- Cite specific data points (e.g., 'Flight UA123 has an average delay of 45.2 minutes')")
        prompt_parts.append("- If the data is insufficient to answer, clearly state what information is missing")
        prompt_parts.append("- Do NOT make up or assume information not present in the data")
        prompt_parts.append("- Use the entity format [FLIGHT:number], [AIRPORT:code] when mentioning specific entities")
    
    elif task_type == "recommendation":
        prompt_parts.append("Provide ranked recommendations based on the data above.")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- Explain why each recommendation is suitable")
        prompt_parts.append("- Consider multiple factors (delay, passenger satisfaction, etc.)")
        prompt_parts.append("- Mention any trade-offs")
        prompt_parts.append("- Be specific with flight numbers and statistics")
    
    elif task_type == "insights":
        prompt_parts.append("Analyze the data and provide actionable insights for airline operations.")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- Identify patterns and trends")
        prompt_parts.append("- Highlight problematic routes or flights")
        prompt_parts.append("- Suggest concrete improvements")
        prompt_parts.append("- Support claims with specific numbers")
    
    prompt_parts.append("")
    
    # 5. USER QUESTION
    prompt_parts.append(f"=== USER QUESTION ===")
    prompt_parts.append(user_query)
    prompt_parts.append("")
    
    prompt_parts.append(f"=== YOUR ANSWER ===")
    
    return "\n".join(prompt_parts)


def build_system_message(task_type: str = "qa") -> str:
    """
    Create a system message for models that support it (like GPT, Claude).
    
    Args:
        task_type: Type of task
    
    Returns:
        System message string
    """
    system_messages = {
        "qa": """You are an airline data analyst assistant. Your role is to answer questions 
about flights, routes, delays, and passenger satisfaction using data from a knowledge graph.

Key principles:
1. Only use information explicitly provided in the context
2. Be precise with numbers and entity references
3. Admit when data is insufficient
4. Never hallucinate or make assumptions
5. Use entity tags like [FLIGHT:UA123] for traceability""",
        
        "recommendation": """You are a flight recommendation assistant for airline operations.
Analyze flight performance data to provide actionable recommendations.

Key principles:
1. Consider multiple factors (delays, satisfaction scores, frequency)
2. Explain trade-offs clearly
3. Support recommendations with specific data
4. Prioritize operational reliability
5. Use entity tags for traceability""",
        
        "insights": """You are a senior airline operations analyst. Analyze flight data
to identify patterns, problems, and opportunities for improvement.

Key principles:
1. Look for trends across routes and flights
2. Quantify issues with specific metrics
3. Suggest concrete, actionable improvements
4. Consider business impact
5. Support claims with data"""
    }
    
    return system_messages.get(task_type, system_messages["qa"])


def extract_entity_references(llm_response: str) -> list:
    """
    Extract entity references from LLM response (e.g., [FLIGHT:UA123]).
    Useful for validation and linking back to the graph.
    
    Args:
        llm_response: The LLM's answer text
    
    Returns:
        List of (entity_type, entity_id) tuples
    """
    import re
    pattern = r'\[([A-Z]+):([^\]]+)\]'
    matches = re.findall(pattern, llm_response)
    return matches


# Test function
if __name__ == "__main__":
    # Sample usage
    sample_query = "Which flights from ORD to LAX have the worst delays?"
    
    sample_context = """=== KNOWLEDGE GRAPH INFORMATION ===

Record 1:
  flight_number: UA123
  fleet: Boeing 737
  avg_arrival_delay: 45.20
  feedback_count: 156

Record 2:
  flight_number: AA456
  fleet: Airbus A320
  avg_arrival_delay: 12.50
  feedback_count: 203
"""
    
    sample_provenance = """=== DATA PROVENANCE ===
All information retrieved from Neo4j Knowledge Graph:
Total records retrieved: 2
Entity types involved: Flights
"""
    
    print("=== Testing Prompt Builder ===\n")
    
    # Test QA prompt
    print("1. QA Task Prompt:")
    print("-" * 80)
    qa_prompt = build_prompt(sample_query, sample_context, sample_provenance, "qa")
    print(qa_prompt)
    
    print("\n\n2. System Message:")
    print("-" * 80)
    print(build_system_message("qa"))
    
    print("\n\n3. Entity Extraction Test:")
    print("-" * 80)
    sample_response = "Based on the data, [FLIGHT:UA123] has the highest delay at [AIRPORT:ORD]."
    entities = extract_entity_references(sample_response)
    print(f"Found entities: {entities}")