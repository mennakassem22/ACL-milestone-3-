# backend/llm_caller.py

import requests
import json
from typing import Dict, Optional
import time

# ============================================================================
# FREE LLM OPTIONS
# ============================================================================

class LLMCaller:
    """
    Unified interface for calling different LLM APIs.
    Supports multiple free options for testing.
    """
    
    def __init__(self, model_name: str = "groq-llama", api_key: Optional[str] = None):
        """
        Initialize LLM caller.
        
        Args:
            model_name: One of ["groq-llama", "groq-mixtral", "hf-mistral", "hf-gemma", "ollama-llama"]
            api_key: API key (required for Groq and HuggingFace)
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = self._get_base_url()
        self.model_id = self._get_model_id()
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL for the model."""
        if self.model_name.startswith("groq"):
            return "https://api.groq.com/openai/v1/chat/completions"
        elif self.model_name.startswith("hf"):
            return "https://api-inference.huggingface.co/models"
        elif self.model_name.startswith("ollama"):
            return "http://localhost:11434/api/generate"
        else:
            raise ValueError(f"Unknown model: {self.model_name}")
    
    def _get_model_id(self) -> str:
        """Get the specific model ID for the API."""
        model_map = {
            "groq-llama": "llama-3.3-70b-versatile",
            "groq-mixtral": "mixtral-8x7b-32768",
            "hf-mistral": "mistralai/Mistral-7B-Instruct-v0.2",
            "hf-gemma": "google/gemma-2-2b-it",
            "ollama-llama": "llama3.2"
        }
        return model_map.get(self.model_name, "llama-3.3-70b-versatile")
    
    def call(self, prompt: str, system_message: Optional[str] = None, 
            max_tokens: int = 1000, temperature: float = 0.1) -> Dict:
        """
        Call the LLM with a prompt.
        
        Args:
            prompt: The user prompt
            system_message: Optional system message
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Dict with 'response', 'model', 'tokens', 'time' keys
        """
        start_time = time.time()
        
        try:
            if self.model_name.startswith("groq"):
                response = self._call_groq(prompt, system_message, max_tokens, temperature)
            elif self.model_name.startswith("hf"):
                response = self._call_huggingface(prompt, max_tokens, temperature)
            elif self.model_name.startswith("ollama"):
                response = self._call_ollama(prompt, max_tokens, temperature)
            else:
                response = {"error": "Unknown model type"}
            
            response["time"] = time.time() - start_time
            response["model"] = self.model_name
            return response
            
        except Exception as e:
            return {
                "error": str(e),
                "model": self.model_name,
                "time": time.time() - start_time
            }
    
    def _call_groq(self, prompt: str, system_message: Optional[str], 
                   max_tokens: int, temperature: float) -> Dict:
        """Call Groq API (very fast, free tier available)."""
        if not self.api_key:
            return {"error": "Groq API key required. Get one free at https://console.groq.com"}
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(self.base_url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        return {
            "response": result["choices"][0]["message"]["content"],
            "tokens": result.get("usage", {}).get("total_tokens", 0)
        }
    
    def _call_huggingface(self, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """Call HuggingFace Inference API (free but slower)."""
        if not self.api_key:
            return {"error": "HuggingFace API key required. Get one free at https://huggingface.co/settings/tokens"}
        
        url = f"{self.base_url}/{self.model_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        # HuggingFace returns different formats
        if isinstance(result, list) and len(result) > 0:
            text = result[0].get("generated_text", "")
        else:
            text = result.get("generated_text", str(result))
        
        return {
            "response": text,
            "tokens": len(text.split())  # Rough estimate
        }
    
    def _call_ollama(self, prompt: str, max_tokens: int, temperature: float) -> Dict:
        """Call local Ollama (100% free, runs locally)."""
        data = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        try:
            response = requests.post(self.base_url, json=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            return {
                "response": result.get("response", ""),
                "tokens": result.get("eval_count", 0)
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Ollama not running. Install with: curl -fsSL https://ollama.com/install.sh | sh"}


def compare_models(prompt: str, models: list, api_keys: Dict[str, str] = None) -> Dict:
    """
    Compare multiple models on the same prompt.
    
    Args:
        prompt: The prompt to test
        models: List of model names
        api_keys: Dict mapping model families to API keys
    
    Returns:
        Dict with results for each model
    """
    api_keys = api_keys or {}
    results = {}
    
    for model in models:
        print(f"Testing {model}...")
        
        # Get API key for this model family
        model_family = model.split("-")[0]  # "groq", "hf", "ollama"
        api_key = api_keys.get(model_family)
        
        caller = LLMCaller(model, api_key)
        result = caller.call(prompt)
        results[model] = result
        
        # Rate limiting pause
        time.sleep(1)
    
    return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=== LLM Caller Test ===\n")
    
    # Simple test prompt
    test_prompt = """Based on the following data, which flight has the worst delay?

Flight UA123: avg delay = 45.2 minutes
Flight AA456: avg delay = 12.5 minutes

Answer concisely."""
    
    # Test with different models (you'll need API keys)
    # Get free keys from:
    # - Groq: https://console.groq.com (RECOMMENDED - very fast and free)
    # - HuggingFace: https://huggingface.co/settings/tokens
    
    # Example with Groq (fastest)
    print("1. Testing Groq (if you have API key):")
    groq_key = input("Enter Groq API key (or press Enter to skip): ").strip()
    if groq_key:
        caller = LLMCaller("groq-llama", groq_key)
        result = caller.call(test_prompt)
        print(f"Response: {result.get('response', result.get('error'))}")
        print(f"Time: {result.get('time', 0):.2f}s")
        print(f"Tokens: {result.get('tokens', 0)}")
    
    print("\n2. Testing local Ollama (if installed):")
    ollama_caller = LLMCaller("ollama-llama")
    result = ollama_caller.call(test_prompt)
    print(f"Response: {result.get('response', result.get('error'))}")
    
    print("\n" + "="*80)
    print("SETUP INSTRUCTIONS:")
    print("="*80)
    print("""
1. GROQ (Recommended - Free & Fast):
   - Sign up: https://console.groq.com
   - Get API key
   - Very fast inference, generous free tier

2. HUGGINGFACE (Free but slower):
   - Sign up: https://huggingface.co
   - Get token: https://huggingface.co/settings/tokens
   
3. OLLAMA (100% Free, runs locally):
   - Install: curl -fsSL https://ollama.com/install.sh | sh
   - Run: ollama run llama3.2
   - No API key needed!
""")