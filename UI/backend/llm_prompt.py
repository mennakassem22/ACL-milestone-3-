# backend/llm_prompt.py - ENHANCED VERSION

from typing import Optional

def build_prompt(user_query: str, 
                grounding_context: str, 
                provenance: Optional[str] = None,
                task_type: str = "qa") -> str:
    """
    Build a structured prompt with context, persona, and task.
    Enhanced with better data interpretation guidelines.
    
    Args:
        user_query: The original user question
        grounding_context: The formatted graph data (from grounding_builder)
        provenance: Optional provenance information
        task_type: Type of task ("qa", "recommendation", "booking", "insights")
    
    Returns:
        Complete prompt string for the LLM
    """
    
    # Define persona based on task type
    personas = {
        "qa": "You are an expert airline data analyst with deep knowledge of flight operations and passenger satisfaction metrics.",
        "recommendation": "You are a professional flight recommendation assistant specializing in airline operations optimization.",
        "booking": "You are an experienced travel booking assistant with expertise in flight selection.",
        "insights": "You are a senior airline operations analyst with 10+ years of experience in data-driven decision making."
    }
    
    persona = personas.get(task_type, personas["qa"])
    
    # Build the structured prompt
    prompt_parts = []
    
    # 1. PERSONA
    prompt_parts.append("=== YOUR ROLE ===")
    prompt_parts.append(persona)
    prompt_parts.append("")
    
    # 2. DATA INTERPRETATION GUIDE (CRITICAL!)
    prompt_parts.append("=== DATA INTERPRETATION GUIDE ===")
    prompt_parts.append("IMPORTANT - Understand these data conventions:")
    prompt_parts.append("")
    prompt_parts.append("**Delay/Arrival Times:**")
    prompt_parts.append("- arrival_delay_minutes: NEGATIVE = arrived EARLY (GOOD), POSITIVE = arrived LATE (BAD)")
    prompt_parts.append("- Example: -18 minutes = arrived 18 minutes EARLY (excellent on-time performance)")
    prompt_parts.append("- Example: +45 minutes = arrived 45 minutes LATE (poor performance)")
    prompt_parts.append("")
    prompt_parts.append("**Satisfaction Scores:**")
    prompt_parts.append("- All satisfaction scores use a 1-5 scale where:")
    prompt_parts.append("  * 5.0 = Excellent (very satisfied)")
    prompt_parts.append("  * 4.0 = Good (satisfied)")
    prompt_parts.append("  * 3.0 = Average (neutral)")
    prompt_parts.append("  * 2.0 = Poor (dissatisfied)")
    prompt_parts.append("  * 1.0 = Very Poor (very dissatisfied)")
    prompt_parts.append("- food_satisfaction_score, seat_comfort_score, entertainment_score all use this scale")
    prompt_parts.append("")
    prompt_parts.append("**What Constitutes a 'Complaint':**")
    prompt_parts.append("- Satisfaction score < 3.0 (below average)")
    prompt_parts.append("- Positive delay (flight arrived late)")
    prompt_parts.append("- Multiple connection issues (number_of_legs > 2)")
    prompt_parts.append("- If scores are HIGH (4-5) and delay is NEGATIVE (early), there are NO complaints")
    prompt_parts.append("")
    
    # 3. AVAILABLE DATA
    prompt_parts.append("=== AVAILABLE DATA ===")
    prompt_parts.append(grounding_context)
    prompt_parts.append("")
    
    # 4. PROVENANCE (if provided)
    if provenance:
        prompt_parts.append(provenance)
        prompt_parts.append("")
    
    # 5. TASK INSTRUCTIONS (Enhanced)
    prompt_parts.append("=== YOUR TASK ===")
    
    if task_type == "qa":
        prompt_parts.append("Answer the user's question using ONLY the information provided above.")
        prompt_parts.append("")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- ALWAYS interpret delays correctly: negative = early (good), positive = late (bad)")
        prompt_parts.append("- ALWAYS interpret satisfaction scores: 5 = excellent, 1 = poor")
        prompt_parts.append("- Be precise and factual with specific numbers")
        prompt_parts.append("- Cite specific data points (e.g., 'Flight 1004 arrived 18 minutes early')")
        prompt_parts.append("- If asking about complaints, check if scores are low (<3) or delays are positive")
        prompt_parts.append("- If data shows high scores and early arrival, clearly state 'No complaints found'")
        prompt_parts.append("- If the data is insufficient, clearly state what information is missing")
        prompt_parts.append("- Do NOT make up or assume information not present in the data")
        prompt_parts.append("- Use natural language, avoid jargon")
    
    elif task_type == "recommendation":
        prompt_parts.append("Provide ranked recommendations based on the data above.")
        prompt_parts.append("")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- Prioritize flights with NEGATIVE delays (early arrivals)")
        prompt_parts.append("- Prioritize flights with HIGH satisfaction scores (4.0+)")
        prompt_parts.append("- Explain why each recommendation is suitable")
        prompt_parts.append("- Consider multiple factors: on-time performance, passenger satisfaction, reliability")
        prompt_parts.append("- Mention any trade-offs clearly")
        prompt_parts.append("- Be specific with flight numbers and statistics")
        prompt_parts.append("- Rank from best to worst")
    
    elif task_type == "insights":
        prompt_parts.append("Analyze the data and provide actionable insights for airline operations.")
        prompt_parts.append("")
        prompt_parts.append("Guidelines:")
        prompt_parts.append("- Identify flights/routes with consistently positive delays (late arrivals)")
        prompt_parts.append("- Highlight flights with low satisfaction scores (<3.0)")
        prompt_parts.append("- Look for patterns and trends")
        prompt_parts.append("- Suggest concrete improvements")
        prompt_parts.append("- Support all claims with specific numbers from the data")
        prompt_parts.append("- Distinguish between operational issues and passenger satisfaction issues")
    
    prompt_parts.append("")
    
    # 6. USER QUESTION
    prompt_parts.append("=== USER QUESTION ===")
    prompt_parts.append(user_query)
    prompt_parts.append("")
    
    # 7. RESPONSE FORMAT
    prompt_parts.append("=== RESPONSE FORMAT ===")
    prompt_parts.append("Structure your answer clearly:")
    prompt_parts.append("1. Start with a direct answer to the question")
    prompt_parts.append("2. Provide supporting evidence from the data")
    prompt_parts.append("3. Use bullet points for multiple items")
    prompt_parts.append("4. End with a brief summary or recommendation if appropriate")
    prompt_parts.append("")
    
    prompt_parts.append("=== YOUR ANSWER ===")
    
    return "\n".join(prompt_parts)


def build_system_message(task_type: str = "qa") -> str:
    """
    Create a system message for models that support it (like GPT, Claude).
    Enhanced with better data interpretation guidance.
    
    Args:
        task_type: Type of task
    
    Returns:
        System message string
    """
    system_messages = {
        "qa": """You are an expert airline data analyst. Answer questions about flights, routes, delays, and passenger satisfaction using provided data.

CRITICAL DATA CONVENTIONS:
- Negative delay = EARLY arrival (GOOD) | Positive delay = LATE arrival (BAD)
- Satisfaction scores: 5=Excellent, 4=Good, 3=Average, 2=Poor, 1=Very Poor
- Complaints = low scores (<3) OR late arrivals (positive delay)

Key principles:
1. Only use information explicitly provided
2. Interpret delays and scores correctly
3. Be precise with numbers and interpretations
4. Admit when data is insufficient
5. Never hallucinate or make assumptions
6. Use clear, natural language""",
        
        "recommendation": """You are a flight recommendation assistant for airline operations.

CRITICAL DATA CONVENTIONS:
- Negative delay = EARLY arrival (GOOD) | Positive delay = LATE arrival (BAD)
- Satisfaction scores: 5=Excellent, 1=Poor
- Recommend flights with: negative delays + high satisfaction scores

Key principles:
1. Prioritize on-time performance (negative delays)
2. Consider passenger satisfaction scores
3. Explain trade-offs clearly
4. Support recommendations with specific data
5. Rank recommendations from best to worst""",
        
        "insights": """You are a senior airline operations analyst.

CRITICAL DATA CONVENTIONS:
- Negative delay = EARLY arrival | Positive delay = LATE arrival
- Satisfaction scores: 5=Excellent, 1=Poor
- Problems = positive delays + low satisfaction scores

Key principles:
1. Identify operational issues (late arrivals)
2. Identify satisfaction issues (low scores)
3. Quantify problems with specific metrics
4. Suggest concrete, actionable improvements
5. Support all claims with data"""
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


def validate_response_quality(llm_response: str, grounding_context: str) -> dict:
    """
    Validate the quality of LLM response.
    Checks for common mistakes in interpretation.
    
    Args:
        llm_response: The LLM's generated answer
        grounding_context: The original context provided
    
    Returns:
        Dict with validation results and warnings
    """
    warnings = []
    
    # Check for common misinterpretations
    if "complaint" in llm_response.lower() and "5.0" in grounding_context:
        if "excellent" not in llm_response.lower() and "satisfied" not in llm_response.lower():
            warnings.append("Possible misinterpretation: 5.0 score should be positive")
    
    if "-" in grounding_context and "delay" in grounding_context:
        if "late" in llm_response.lower() and "early" not in llm_response.lower():
            warnings.append("Possible misinterpretation: negative delay means early arrival")
    
    return {
        "has_warnings": len(warnings) > 0,
        "warnings": warnings,
        "response_length": len(llm_response),
        "mentions_data": any(word in llm_response.lower() for word in ["flight", "delay", "score", "passenger"])
    }


# Test function
if __name__ == "__main__":
    print("=== Testing Enhanced Prompt Builder ===\n")
    
    # Test Case 1: Complaint query with good data
    sample_query_1 = "Show complaints about flight 1004"
    sample_context_1 = """=== KNOWLEDGE GRAPH INFORMATION ===

Record 1:
  flight_number: 1004
  passenger: LHXX2P
  feedback_id: F_2778
  food_satisfaction_score: 5.00
  arrival_delay_minutes: -18.00
  number_of_legs: 1
"""
    
    print("TEST 1: Complaint Query with Good Data")
    print("-" * 80)
    prompt_1 = build_prompt(sample_query_1, sample_context_1, None, "qa")
    print(prompt_1[:1500])
    print("\n[Truncated for readability]\n")
    
    # Test Case 2: Recommendation query
    sample_query_2 = "Recommend the best flight from ORX to LAX"
    sample_context_2 = """=== KNOWLEDGE GRAPH INFORMATION ===

Record 1:
  flight_number: 1004
  avg_arrival_delay: -15.5
  avg_food_score: 4.8
  
Record 2:
  flight_number: 1005
  avg_arrival_delay: 25.3
  avg_food_score: 3.2
"""
    
    print("\nTEST 2: Recommendation Query")
    print("-" * 80)
    prompt_2 = build_prompt(sample_query_2, sample_context_2, None, "recommendation")
    print("Prompt includes:")
    print("✅ Data interpretation guide")
    print("✅ Recommendation-specific instructions")
    print("✅ Negative delay = early (good)")
    print("✅ High scores = satisfied passengers")
    
    # Test Case 3: System Message
    print("\nTEST 3: Enhanced System Message")
    print("-" * 80)
    system_msg = build_system_message("qa")
    print(system_msg)
    
    # Test Case 4: Response Validation
    print("\n\nTEST 4: Response Validation")
    print("-" * 80)
    
    bad_response = "Flight 1004 had complaints with delay of -18 minutes being late"
    validation = validate_response_quality(bad_response, sample_context_1)
    
    print(f"Response: {bad_response}")
    print(f"Validation: {validation}")
    
    print("\n✅ Enhanced prompt builder complete!")
    print("\nKey improvements:")
    print("1. ✅ Clear data interpretation guide")
    print("2. ✅ Explains negative delay = early")
    print("3. ✅ Defines satisfaction score scale")
    print("4. ✅ Specifies what counts as complaint")
    print("5. ✅ Better task-specific instructions")
    print("6. ✅ Response validation function")