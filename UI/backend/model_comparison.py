# backend/model_comparison.py

import time
import json
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from llm_caller import LLMCaller

class ModelComparator:
    """
    Compares multiple LLM models on the same queries with quantitative and qualitative metrics.
    """
    
    # Define test models with their configurations
    MODELS = {
        "ollama-llama": {
            "name": "Llama 3.2 (Ollama)",
            "type": "local",
            "cost_per_1k": 0.0,
            "requires_api_key": False
        },
        "hf-mistral": {
            "name": "Mistral 7B (HuggingFace)",
            "type": "cloud",
            "cost_per_1k": 0.0,  # Free tier
            "requires_api_key": True
        },
        "hf-gemma": {
            "name": "Gemma 2B (HuggingFace)",
            "type": "cloud",
            "cost_per_1k": 0.0,  # Free tier
            "requires_api_key": True
        }
    }
    
    # Standard test cases for evaluation
    TEST_CASES = [
        {
            "id": 1,
            "query": "Which flight has the highest average delay?",
            "intent": "delay_query",
            "expected_entities": ["delay", "flight"],
            "difficulty": "easy"
        },
        {
            "id": 2,
            "query": "Show me flights from ORX to LAX with their on-time performance",
            "intent": "flight_search",
            "expected_entities": ["origin:ORX", "destination:LAX"],
            "difficulty": "medium"
        },
        {
            "id": 3,
            "query": "What are the top 3 routes with the worst delay patterns and why?",
            "intent": "route_stats",
            "expected_entities": ["route", "delay"],
            "difficulty": "hard"
        },
        {
            "id": 4,
            "query": "Analyze passenger complaints for flight 1004",
            "intent": "complaints_search",
            "expected_entities": ["flight_number:1004"],
            "difficulty": "medium"
        },
        {
            "id": 5,
            "query": "Recommend the best flight considering delays and passenger satisfaction",
            "intent": "recommendation",
            "expected_entities": ["delay", "satisfaction"],
            "difficulty": "hard"
        }
    ]
    
    def __init__(self, api_keys: Dict[str, str] = None):
        """
        Initialize comparator with API keys for cloud models.
        
        Args:
            api_keys: Dict mapping model identifiers to API keys
        """
        self.api_keys = api_keys or {}
        self.results = []
    
    def run_comparison(self, 
                      test_cases: List[Dict] = None,
                      models: List[str] = None,
                      grounding_data: Dict[str, Any] = None,
                      max_tokens: int = 800,
                      temperature: float = 0.2) -> pd.DataFrame:
        """
        Run comparison across multiple models and test cases.
        
        Args:
            test_cases: List of test case dicts (uses defaults if None)
            models: List of model identifiers to test (uses all if None)
            grounding_data: Dict mapping test case IDs to grounding context
            max_tokens: Max tokens for responses
            temperature: Temperature for generation
            
        Returns:
            DataFrame with comparison results
        """
        if test_cases is None:
            test_cases = self.TEST_CASES
        
        if models is None:
            models = list(self.MODELS.keys())
        
        self.results = []
        
        for test_case in test_cases:
            query = test_case["query"]
            test_id = test_case["id"]
            
            # Get grounding for this test case
            grounding = grounding_data.get(test_id, "") if grounding_data else ""
            provenance = "Sample provenance data"
            
            # Build prompt
            from llm_prompt import build_prompt, build_system_message
            task_type = "recommendation" if test_case["intent"] == "recommendation" else "qa"
            prompt = build_prompt(query, grounding, provenance, task_type)
            system_msg = build_system_message(task_type)
            
            for model_id in models:
                model_info = self.MODELS.get(model_id)
                if not model_info:
                    continue
                
                # Check if API key needed
                if model_info["requires_api_key"] and model_id not in self.api_keys:
                    print(f"Skipping {model_id}: No API key provided")
                    continue
                
                # Run model
                result = self._run_single_model(
                    model_id=model_id,
                    query=query,
                    prompt=prompt,
                    system_msg=system_msg,
                    test_case=test_case,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                self.results.append(result)
        
        return self.get_results_dataframe()
    
    def _run_single_model(self,
                         model_id: str,
                         query: str,
                         prompt: str,
                         system_msg: str,
                         test_case: Dict,
                         max_tokens: int,
                         temperature: float) -> Dict:
        """Run a single model on a test case and collect metrics."""
        
        model_info = self.MODELS[model_id]
        api_key = self.api_keys.get(model_id)
        
        start_time = time.time()
        
        try:
            caller = LLMCaller(model_id, api_key)
            result = caller.call(prompt, system_msg, max_tokens=max_tokens, temperature=temperature)
            
            response_time = time.time() - start_time
            
            if "error" in result:
                return {
                    "test_id": test_case["id"],
                    "query": query,
                    "model": model_info["name"],
                    "model_id": model_id,
                    "difficulty": test_case["difficulty"],
                    "response": None,
                    "error": result["error"],
                    "response_time": response_time,
                    "success": False,
                    "tokens_used": 0,
                    "cost": 0.0
                }
            
            # Estimate token usage (rough approximation)
            tokens_used = len(result['response'].split()) * 1.3  # Words to tokens ratio
            cost = (tokens_used / 1000) * model_info["cost_per_1k"]
            
            return {
                "test_id": test_case["id"],
                "query": query,
                "model": model_info["name"],
                "model_id": model_id,
                "difficulty": test_case["difficulty"],
                "response": result['response'],
                "error": None,
                "response_time": response_time,
                "success": True,
                "tokens_used": int(tokens_used),
                "cost": cost,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "test_id": test_case["id"],
                "query": query,
                "model": model_info["name"],
                "model_id": model_id,
                "difficulty": test_case["difficulty"],
                "response": None,
                "error": str(e),
                "response_time": time.time() - start_time,
                "success": False,
                "tokens_used": 0,
                "cost": 0.0
            }
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame for analysis."""
        return pd.DataFrame(self.results)
    
    def calculate_quantitative_metrics(self) -> pd.DataFrame:
        """
        Calculate quantitative metrics for each model.
        
        Returns:
            DataFrame with aggregated metrics per model
        """
        if not self.results:
            return pd.DataFrame()
        
        df = self.get_results_dataframe()
        
        # Group by model and calculate metrics
        metrics = df.groupby('model').agg({
            'success': ['sum', 'count'],
            'response_time': ['mean', 'std', 'min', 'max'],
            'tokens_used': 'sum',
            'cost': 'sum'
        }).round(3)
        
        # Flatten column names
        metrics.columns = ['_'.join(col).strip() for col in metrics.columns.values]
        
        # Calculate success rate
        metrics['success_rate'] = (metrics['success_sum'] / metrics['success_count'] * 100).round(1)
        
        # Rename columns for clarity
        metrics = metrics.rename(columns={
            'success_count': 'total_tests',
            'success_sum': 'successful_tests',
            'response_time_mean': 'avg_response_time',
            'response_time_std': 'std_response_time',
            'response_time_min': 'min_response_time',
            'response_time_max': 'max_response_time',
            'tokens_used_sum': 'total_tokens',
            'cost_sum': 'total_cost'
        })
        
        return metrics
    
    def get_qualitative_template(self) -> List[Dict]:
        """
        Get template for manual qualitative evaluation.
        
        Returns:
            List of dicts ready for human annotation
        """
        template = []
        
        for result in self.results:
            if not result['success']:
                continue
            
            template.append({
                "test_id": result["test_id"],
                "query": result["query"],
                "model": result["model"],
                "response": result["response"],
                "relevance_score": None,  # 1-5
                "accuracy_score": None,   # 1-5
                "completeness_score": None,  # 1-5
                "naturalness_score": None,   # 1-5
                "overall_score": None,    # 1-5
                "comments": ""
            })
        
        return template
    
    def save_results(self, filepath: str = "model_comparison_results.json"):
        """Save results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump({
                "results": self.results,
                "quantitative_metrics": self.calculate_quantitative_metrics().to_dict(),
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        print(f"Results saved to {filepath}")
    
    def generate_comparison_report(self) -> str:
        """Generate a markdown report of the comparison."""
        if not self.results:
            return "No results to report."
        
        metrics = self.calculate_quantitative_metrics()
        
        report = ["# LLM Model Comparison Report\n"]
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Total Tests:** {len(self.results)}\n\n")
        
        report.append("## Quantitative Metrics\n\n")
        report.append("### Overall Performance\n\n")
        report.append(metrics.to_markdown())
        report.append("\n\n")
        
        report.append("### Performance by Difficulty\n\n")
        df = self.get_results_dataframe()
        difficulty_metrics = df[df['success']].groupby(['model', 'difficulty'])['response_time'].mean().unstack()
        report.append(difficulty_metrics.to_markdown())
        report.append("\n\n")
        
        report.append("## Key Findings\n\n")
        
        # Best average response time
        best_speed = metrics['avg_response_time'].idxmin()
        report.append(f"- **Fastest Model:** {best_speed} ({metrics.loc[best_speed, 'avg_response_time']:.2f}s avg)\n")
        
        # Best success rate
        best_success = metrics['success_rate'].idxmax()
        report.append(f"- **Most Reliable:** {best_success} ({metrics.loc[best_success, 'success_rate']:.1f}% success rate)\n")
        
        # Lowest cost
        cheapest = metrics['total_cost'].idxmin()
        report.append(f"- **Most Cost-Effective:** {cheapest} (${metrics.loc[cheapest, 'total_cost']:.4f} total)\n")
        
        report.append("\n## Individual Test Results\n\n")
        for result in self.results:
            report.append(f"### Test {result['test_id']}: {result['query'][:60]}...\n\n")
            report.append(f"**Model:** {result['model']}  \n")
            report.append(f"**Difficulty:** {result['difficulty']}  \n")
            report.append(f"**Status:** {'✅ Success' if result['success'] else '❌ Failed'}  \n")
            report.append(f"**Response Time:** {result['response_time']:.2f}s  \n")
            if result['success']:
                report.append(f"**Tokens:** {result['tokens_used']}  \n")
                report.append(f"\n**Response:**\n{result['response'][:200]}...\n\n")
            else:
                report.append(f"**Error:** {result['error']}\n\n")
            report.append("---\n\n")
        
        return "".join(report)


# Example usage
if __name__ == "__main__":
    # Initialize comparator
    comparator = ModelComparator(api_keys={
        "hf-mistral": "your_hf_token_here"
    })
    
    # Sample grounding data for test cases
    grounding_data = {
        1: "Flight 1004: avg_delay=45min | Flight 1005: avg_delay=12min",
        2: "Flight 1001 ORX→LAX: on_time=85% | Flight 1002 ORX→LAX: on_time=92%",
        # ... more grounding for other test cases
    }
    
    # Run comparison
    print("Running model comparison...")
    results_df = comparator.run_comparison(
        models=["ollama-llama", "hf-mistral"],
        grounding_data=grounding_data
    )
    
    # Display results
    print("\n=== RESULTS ===")
    print(results_df)
    
    print("\n=== QUANTITATIVE METRICS ===")
    print(comparator.calculate_quantitative_metrics())
    
    # Save results
    comparator.save_results()
    
    # Generate report
    report = comparator.generate_comparison_report()
    with open("comparison_report.md", "w") as f:
        f.write(report)
    print("\nReport saved to comparison_report.md")