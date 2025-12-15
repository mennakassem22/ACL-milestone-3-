# backend/evaluation_metrics.py

"""
Automated evaluation metrics for LLM responses.
Provides both quantitative and qualitative automated assessments.
"""

from typing import Dict, List, Any
import re
from collections import Counter
import numpy as np

class ResponseEvaluator:
    """Automated metrics for evaluating LLM responses."""
    
    @staticmethod
    def calculate_response_length(response: str) -> Dict[str, int]:
        """Calculate various length metrics."""
        words = response.split()
        sentences = re.split(r'[.!?]+', response)
        
        return {
            "char_count": len(response),
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "avg_word_length": np.mean([len(w) for w in words]) if words else 0,
            "avg_sentence_length": len(words) / max(len(sentences), 1)
        }
    
    @staticmethod
    def check_information_presence(response: str, expected_entities: List[str]) -> Dict[str, Any]:
        """
        Check if expected entities/information are present in response.
        
        Args:
            response: LLM response text
            expected_entities: List of expected terms/entities
            
        Returns:
            Dict with presence metrics
        """
        response_lower = response.lower()
        
        found_entities = []
        missing_entities = []
        
        for entity in expected_entities:
            if entity.lower() in response_lower:
                found_entities.append(entity)
            else:
                missing_entities.append(entity)
        
        return {
            "found_count": len(found_entities),
            "missing_count": len(missing_entities),
            "coverage_rate": len(found_entities) / len(expected_entities) if expected_entities else 0,
            "found_entities": found_entities,
            "missing_entities": missing_entities
        }
    
    @staticmethod
    def assess_specificity(response: str) -> Dict[str, Any]:
        """
        Assess how specific/detailed the response is.
        Uses heuristics like number presence, named entities, etc.
        """
        # Count numbers (indicates specificity)
        numbers = re.findall(r'\b\d+\.?\d*\b', response)
        
        # Count proper nouns (capitalized words, but not sentence starts)
        words = response.split()
        proper_nouns = []
        for i, word in enumerate(words):
            if i > 0 and word[0].isupper() and len(word) > 1:
                proper_nouns.append(word)
        
        # Check for vague language
        vague_terms = ['maybe', 'perhaps', 'might', 'could', 'some', 'many', 'several', 'various']
        vague_count = sum(1 for term in vague_terms if term in response.lower())
        
        # Check for concrete terms
        concrete_terms = ['flight', 'delay', 'passenger', 'route', 'airport', 'time', 'rating']
        concrete_count = sum(1 for term in concrete_terms if term in response.lower())
        
        specificity_score = (len(numbers) * 2 + len(proper_nouns) + concrete_count - vague_count * 0.5) / len(words) * 100
        
        return {
            "number_count": len(numbers),
            "proper_noun_count": len(proper_nouns),
            "vague_term_count": vague_count,
            "concrete_term_count": concrete_count,
            "specificity_score": max(0, min(100, specificity_score))
        }
    
    @staticmethod
    def check_answer_structure(response: str) -> Dict[str, Any]:
        """Analyze the structure and organization of the response."""
        # Check for list/enumeration
        has_bullet_points = bool(re.search(r'[•\-\*]\s', response))
        has_numbered_list = bool(re.search(r'\d+[\.)]\s', response))
        
        # Check for sections/headers (words followed by colon)
        has_sections = bool(re.search(r'\n[A-Z][^.!?]*:', response))
        
        # Count paragraphs
        paragraphs = [p for p in response.split('\n\n') if p.strip()]
        
        # Check for conclusion/summary indicators
        conclusion_terms = ['in conclusion', 'to summarize', 'overall', 'in summary', 'therefore']
        has_conclusion = any(term in response.lower() for term in conclusion_terms)
        
        return {
            "has_bullet_points": has_bullet_points,
            "has_numbered_list": has_numbered_list,
            "has_sections": has_sections,
            "paragraph_count": len(paragraphs),
            "has_conclusion": has_conclusion,
            "structure_score": sum([has_bullet_points, has_numbered_list, has_sections, has_conclusion]) * 25
        }
    
    @staticmethod
    def detect_hallucinations(response: str, grounding_data: str) -> Dict[str, Any]:
        """
        Detect potential hallucinations by checking if facts in response 
        are supported by grounding data.
        
        Note: This is a heuristic approach and not 100% accurate.
        """
        if not grounding_data:
            return {"hallucination_risk": "unknown", "confidence": 0}
        
        response_lower = response.lower()
        grounding_lower = grounding_data.lower()
        
        # Extract numbers from both
        response_numbers = set(re.findall(r'\b\d+\.?\d*\b', response))
        grounding_numbers = set(re.findall(r'\b\d+\.?\d*\b', grounding_data))
        
        # Check if response numbers are in grounding
        unsupported_numbers = response_numbers - grounding_numbers
        
        # Extract flight numbers (format: 4 digits)
        response_flights = set(re.findall(r'\b\d{4}\b', response))
        grounding_flights = set(re.findall(r'\b\d{4}\b', grounding_data))
        unsupported_flights = response_flights - grounding_flights
        
        # Extract airport codes (3 uppercase letters)
        response_airports = set(re.findall(r'\b[A-Z]{3}\b', response))
        grounding_airports = set(re.findall(r'\b[A-Z]{3}\b', grounding_data))
        unsupported_airports = response_airports - grounding_airports
        
        hallucination_score = (
            len(unsupported_numbers) * 10 +
            len(unsupported_flights) * 20 +
            len(unsupported_airports) * 15
        )
        
        risk_level = "low" if hallucination_score < 20 else "medium" if hallucination_score < 50 else "high"
        
        return {
            "hallucination_risk": risk_level,
            "hallucination_score": hallucination_score,
            "unsupported_numbers": list(unsupported_numbers),
            "unsupported_flights": list(unsupported_flights),
            "unsupported_airports": list(unsupported_airports),
            "confidence": max(0, 100 - hallucination_score)
        }
    
    @staticmethod
    def measure_coherence(response: str) -> Dict[str, Any]:
        """
        Measure coherence using simple heuristics.
        Looks for discourse markers, pronoun usage, etc.
        """
        # Discourse markers indicating logical flow
        transition_words = [
            'however', 'therefore', 'furthermore', 'additionally', 'moreover',
            'consequently', 'meanwhile', 'similarly', 'in contrast', 'for example',
            'specifically', 'in fact', 'as a result', 'on the other hand'
        ]
        
        response_lower = response.lower()
        transition_count = sum(1 for word in transition_words if word in response_lower)
        
        # Check for pronoun continuity (indicates reference to previous content)
        pronouns = ['it', 'they', 'this', 'these', 'those', 'which', 'that']
        pronoun_count = sum(1 for pronoun in pronouns if f' {pronoun} ' in response_lower)
        
        # Calculate sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', response) if s.strip()]
        
        # Check for question words (rhetorical questions can indicate structure)
        question_words = ['what', 'when', 'where', 'why', 'how', 'which']
        question_count = sum(1 for word in question_words if response_lower.startswith(word))
        
        coherence_score = (
            transition_count * 10 +
            pronoun_count * 5 +
            (1 if len(sentences) > 2 else 0) * 10
        )
        
        return {
            "transition_word_count": transition_count,
            "pronoun_count": pronoun_count,
            "coherence_score": min(100, coherence_score),
            "avg_words_per_sentence": len(response.split()) / max(len(sentences), 1)
        }
    
    @staticmethod
    def check_factual_consistency(response: str, previous_facts: List[str]) -> Dict[str, Any]:
        """
        Check if response is consistent with previously established facts.
        Useful for multi-turn conversations.
        """
        if not previous_facts:
            return {"consistency": "n/a", "conflicts": []}
        
        conflicts = []
        response_lower = response.lower()
        
        for fact in previous_facts:
            fact_lower = fact.lower()
            # Simple contradiction detection (very basic)
            if 'not' in response_lower and fact_lower.replace('not ', '') in response_lower:
                conflicts.append(f"Possible contradiction with: {fact}")
        
        return {
            "consistency": "good" if not conflicts else "questionable",
            "conflict_count": len(conflicts),
            "conflicts": conflicts
        }
    
    @staticmethod
    def assess_completeness(response: str, question: str) -> Dict[str, Any]:
        """
        Assess if the response adequately addresses the question.
        """
        question_lower = question.lower()
        response_lower = response.lower()
        
        # Extract question type
        question_words = ['what', 'when', 'where', 'why', 'how', 'which', 'who']
        question_type = None
        for qw in question_words:
            if question_lower.startswith(qw):
                question_type = qw
                break
        
        # Check if response addresses the question type
        addresses_question = False
        if question_type == 'what':
            addresses_question = any(word in response_lower for word in ['is', 'are', 'consists', 'includes'])
        elif question_type == 'when':
            addresses_question = bool(re.search(r'\b\d{1,2}:\d{2}|\b\d{4}\b|today|yesterday|tomorrow', response_lower))
        elif question_type == 'where':
            addresses_question = bool(re.search(r'\b[A-Z]{3}\b', response))  # Airport codes
        elif question_type == 'why':
            addresses_question = any(word in response_lower for word in ['because', 'due to', 'since', 'as', 'reason'])
        elif question_type == 'how':
            addresses_question = any(word in response_lower for word in ['by', 'through', 'via', 'using', 'method'])
        
        # Check for hedge words (may indicate incomplete answer)
        hedge_words = ['might', 'possibly', 'unclear', 'uncertain', 'not sure', 'cannot determine']
        hedge_count = sum(1 for hedge in hedge_words if hedge in response_lower)
        
        completeness_score = (
            (50 if addresses_question else 0) +
            (30 if len(response.split()) > 20 else 0) +
            (20 if hedge_count == 0 else -hedge_count * 10)
        )
        
        return {
            "question_type": question_type or "statement",
            "addresses_question": addresses_question,
            "hedge_word_count": hedge_count,
            "completeness_score": max(0, min(100, completeness_score)),
            "response_length_adequate": len(response.split()) > 15
        }
    
    @staticmethod
    def calculate_readability(response: str) -> Dict[str, Any]:
        """
        Calculate readability metrics (simplified Flesch Reading Ease).
        """
        sentences = [s.strip() for s in re.split(r'[.!?]+', response) if s.strip()]
        words = response.split()
        
        if not sentences or not words:
            return {"readability_score": 0, "difficulty": "unknown"}
        
        syllable_count = sum(ResponseEvaluator._count_syllables(word) for word in words)
        
        avg_sentence_length = len(words) / len(sentences)
        avg_syllables_per_word = syllable_count / len(words)
        
        # Simplified Flesch Reading Ease
        flesch_score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables_per_word
        flesch_score = max(0, min(100, flesch_score))
        
        # Interpret score
        if flesch_score >= 80:
            difficulty = "very_easy"
        elif flesch_score >= 60:
            difficulty = "easy"
        elif flesch_score >= 40:
            difficulty = "moderate"
        elif flesch_score >= 20:
            difficulty = "difficult"
        else:
            difficulty = "very_difficult"
        
        return {
            "readability_score": round(flesch_score, 2),
            "difficulty": difficulty,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2)
        }
    
    @staticmethod
    def _count_syllables(word: str) -> int:
        """Count syllables in a word (approximation)."""
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel
        
        # Adjust for silent e
        if word.endswith('e'):
            syllable_count -= 1
        
        # Ensure at least 1 syllable
        if syllable_count == 0:
            syllable_count = 1
        
        return syllable_count
    
    def evaluate_response(self, 
                         response: str,
                         question: str,
                         grounding_data: str = "",
                         expected_entities: List[str] = None) -> Dict[str, Any]:
        """
        Comprehensive evaluation of a single response.
        
        Args:
            response: The LLM response to evaluate
            question: The original question
            grounding_data: The context/grounding provided to LLM
            expected_entities: List of entities that should be mentioned
            
        Returns:
            Dict with all evaluation metrics
        """
        metrics = {
            "response": response[:100] + "..." if len(response) > 100 else response,
            "question": question,
        }
        
        # Length metrics
        metrics["length"] = self.calculate_response_length(response)
        
        # Information coverage
        if expected_entities:
            metrics["coverage"] = self.check_information_presence(response, expected_entities)
        
        # Specificity
        metrics["specificity"] = self.assess_specificity(response)
        
        # Structure
        metrics["structure"] = self.check_answer_structure(response)
        
        # Hallucination detection
        if grounding_data:
            metrics["hallucination"] = self.detect_hallucinations(response, grounding_data)
        
        # Coherence
        metrics["coherence"] = self.measure_coherence(response)
        
        # Completeness
        metrics["completeness"] = self.assess_completeness(response, question)
        
        # Readability
        metrics["readability"] = self.calculate_readability(response)
        
        # Overall quality score (weighted average)
        quality_score = (
            metrics.get("specificity", {}).get("specificity_score", 50) * 0.15 +
            metrics.get("structure", {}).get("structure_score", 50) * 0.15 +
            metrics.get("coherence", {}).get("coherence_score", 50) * 0.20 +
            metrics.get("completeness", {}).get("completeness_score", 50) * 0.25 +
            metrics.get("readability", {}).get("readability_score", 50) * 0.10 +
            (100 - metrics.get("hallucination", {}).get("hallucination_score", 0)) * 0.15
        )
        
        metrics["overall_quality_score"] = round(quality_score, 2)
        
        return metrics


class ComparisonAnalyzer:
    """Analyze and compare multiple model responses."""
    
    def __init__(self):
        self.evaluator = ResponseEvaluator()
    
    def compare_responses(self,
                         responses: Dict[str, str],
                         question: str,
                         grounding_data: str = "",
                         expected_entities: List[str] = None) -> pd.DataFrame:
        """
        Compare multiple model responses side by side.
        
        Args:
            responses: Dict mapping model names to their responses
            question: The question asked
            grounding_data: Context provided
            expected_entities: Expected information
            
        Returns:
            DataFrame with comparison metrics
        """
        import pandas as pd
        
        results = []
        
        for model_name, response in responses.items():
            eval_result = self.evaluator.evaluate_response(
                response=response,
                question=question,
                grounding_data=grounding_data,
                expected_entities=expected_entities
            )
            
            # Flatten the nested dict for DataFrame
            flat_result = {
                "model": model_name,
                "word_count": eval_result["length"]["word_count"],
                "specificity": eval_result["specificity"]["specificity_score"],
                "structure": eval_result["structure"]["structure_score"],
                "coherence": eval_result["coherence"]["coherence_score"],
                "completeness": eval_result["completeness"]["completeness_score"],
                "readability": eval_result["readability"]["readability_score"],
                "overall_quality": eval_result["overall_quality_score"]
            }
            
            if "coverage" in eval_result:
                flat_result["coverage_rate"] = eval_result["coverage"]["coverage_rate"] * 100
            
            if "hallucination" in eval_result:
                flat_result["hallucination_risk"] = eval_result["hallucination"]["hallucination_risk"]
                flat_result["confidence"] = eval_result["hallucination"]["confidence"]
            
            results.append(flat_result)
        
        return pd.DataFrame(results)
    
    def rank_models(self, comparison_df: pd.DataFrame, criteria: str = "overall_quality") -> pd.DataFrame:
        """
        Rank models based on a specific criterion.
        
        Args:
            comparison_df: DataFrame from compare_responses
            criteria: Column name to rank by
            
        Returns:
            Sorted DataFrame with rankings
        """
        if criteria not in comparison_df.columns:
            criteria = "overall_quality"
        
        ranked = comparison_df.sort_values(criteria, ascending=False).copy()
        ranked.insert(0, 'rank', range(1, len(ranked) + 1))
        
        return ranked
    
    def generate_winner_summary(self, comparison_df: pd.DataFrame) -> Dict[str, str]:
        """Generate a summary of which model wins in each category."""
        categories = [
            "specificity", "structure", "coherence", 
            "completeness", "readability", "overall_quality"
        ]
        
        winners = {}
        for cat in categories:
            if cat in comparison_df.columns:
                winner_idx = comparison_df[cat].idxmax()
                winners[cat] = comparison_df.loc[winner_idx, 'model']
        
        return winners


# Example usage and test
if __name__ == "__main__":
    # Test the evaluator
    evaluator = ResponseEvaluator()
    
    test_response = """
    Based on the flight data, Flight 1004 has the highest average delay of 45 minutes,
    while Flight 1005 performs better with only 12 minutes average delay. The main route
    from ORX to LAX shows an 85% on-time performance. Therefore, I recommend considering
    Flight 1005 for better punctuality.
    """
    
    test_question = "Which flight has the highest delay?"
    test_grounding = "Flight 1004: avg_delay=45min | Flight 1005: avg_delay=12min | Route ORX-LAX: on_time=85%"
    test_entities = ["Flight 1004", "delay", "45 minutes"]
    
    print("="*60)
    print("AUTOMATED EVALUATION METRICS TEST")
    print("="*60)
    
    result = evaluator.evaluate_response(
        response=test_response,
        question=test_question,
        grounding_data=test_grounding,
        expected_entities=test_entities
    )
    
    print(f"\n✅ Overall Quality Score: {result['overall_quality_score']}/100")
    print(f"\n📊 Detailed Metrics:")
    print(f"  - Word Count: {result['length']['word_count']}")
    print(f"  - Specificity: {result['specificity']['specificity_score']:.1f}/100")
    print(f"  - Structure: {result['structure']['structure_score']}/100")
    print(f"  - Coherence: {result['coherence']['coherence_score']}/100")
    print(f"  - Completeness: {result['completeness']['completeness_score']}/100")
    print(f"  - Readability: {result['readability']['readability_score']:.1f}/100 ({result['readability']['difficulty']})")
    print(f"  - Hallucination Risk: {result['hallucination']['hallucination_risk']} (confidence: {result['hallucination']['confidence']}%)")
    
    if result.get('coverage'):
        print(f"  - Entity Coverage: {result['coverage']['coverage_rate']*100:.1f}%")
        print(f"    Found: {result['coverage']['found_entities']}")
        print(f"    Missing: {result['coverage']['missing_entities']}")
    
    print("\n" + "="*60)
    
    # Test comparison
    print("\nTesting Model Comparison...")
    analyzer = ComparisonAnalyzer()
    
    test_responses = {
        "Model A": test_response,
        "Model B": "Flight 1004 has delays. It's around 45 minutes maybe. The other flights are better.",
        "Model C": "According to the data, Flight 1004 experiences an average delay of 45 minutes, significantly higher than Flight 1005's 12-minute average. The ORX to LAX route maintains an 85% on-time record. For travelers prioritizing punctuality, Flight 1005 represents the optimal choice given its superior performance metrics."
    }
    
    comparison = analyzer.compare_responses(
        responses=test_responses,
        question=test_question,
        grounding_data=test_grounding,
        expected_entities=test_entities
    )
    
    print("\n📊 Model Comparison:")
    print(comparison.to_string(index=False))
    
    print("\n🏆 Category Winners:")
    winners = analyzer.generate_winner_summary(comparison)
    for category, winner in winners.items():
        print(f"  {category}: {winner}")