# backend/llm_caller.py

import requests
import json
from typing import Dict, Optional
import time

# ============================================================================
# FREE LLM OPTIONS - OLLAMA & HUGGINGFACE
# ============================================================================

class LLMCaller:
    """
    Unified interface for calling different LLM APIs.
    Supports Ollama (local) and HuggingFace (cloud) models.
    """
    
    def __init__(self, model_name: str = "ollama-llama", api_key: Optional[str] = None):
        """
        Initialize LLM caller.
        
        Args:
            model_name: One of ["ollama-llama", "hf-mistral", "hf-gemma"]
            api_key: API key (required for HuggingFace only)
        """
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = self._get_base_url()
        self.model_id = self._get_model_id()
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL for the model."""
        if self.model_name.startswith("hf"):
            return "https://api-inference.huggingface.co/models"
        elif self.model_name.startswith("ollama"):
            return "http://localhost:11434/api/generate"
        else:
            raise ValueError(f"Unknown model: {self.model_name}. Use 'ollama-llama', 'hf-mistral', or 'hf-gemma'")
    
    def _get_model_id(self) -> str:
        """Get the specific model ID for the API."""
        model_map = {
            "hf-mistral": "microsoft/Phi-3-mini-4k-instruct",
            "hf-gemma": "Qwen/Qwen2.5-0.5B-Instruct",
            "ollama-llama": "llama3.2"
        }
        return model_map.get(self.model_name, "llama3.2")
    
    def call(self, prompt: str, system_message: Optional[str] = None, 
            max_tokens: int = 1000, temperature: float = 0.1) -> Dict:
        """
        Call the LLM with a prompt.
        
        Args:
            prompt: The user prompt
            system_message: Optional system message (only used by Ollama)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Dict with 'response', 'model', 'tokens', 'time' keys
        """
        start_time = time.time()
        
        try:
            if self.model_name.startswith("hf"):
                response = self._call_huggingface(prompt, max_tokens, temperature)
            elif self.model_name.startswith("ollama"):
                response = self._call_ollama(prompt, system_message, max_tokens, temperature)
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
    
    def _call_ollama(self, prompt: str, system_message: Optional[str], 
                     max_tokens: int, temperature: float) -> Dict:
        """Call local Ollama (100% free, runs locally)."""
        
        # Combine system message with prompt if provided
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        
        data = {
            "model": self.model_id,
            "prompt": full_prompt,
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
            return {"error": "Ollama not running. Install: curl -fsSL https://ollama.com/install.sh | sh, then run: ollama run llama3.2"}


def compare_models(prompt: str, models: list, api_keys: Dict[str, str] = None) -> Dict:
    """
    Compare multiple models on the same prompt.
    
    Args:
        prompt: The prompt to test
        models: List of model names (e.g., ["ollama-llama", "hf-mistral"])
        api_keys: Dict mapping "hf" to HuggingFace API key
    
    Returns:
        Dict with results for each model
    """
    api_keys = api_keys or {}
    results = {}
    
    for model in models:
        print(f"Testing {model}...")
        
        # Get API key for HuggingFace models
        api_key = None
        if model.startswith("hf"):
            api_key = api_keys.get("hf")
        
        caller = LLMCaller(model, api_key)
        result = caller.call(prompt)
        results[model] = result
        
        # Rate limiting pause for HuggingFace
        if model.startswith("hf"):
            time.sleep(1)
    
    return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("=== LLM Caller Test (Ollama & HuggingFace) ===\n")
    
    # Simple test prompt
    test_prompt = """Based on the following data, which flight has the worst delay?

Flight UA123: avg delay = 45.2 minutes
Flight AA456: avg delay = 12.5 minutes

Answer concisely."""
    
    print("1. Testing local Ollama:")
    print("-" * 50)
    ollama_caller = LLMCaller("ollama-llama")
    result = ollama_caller.call(test_prompt)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Response: {result['response']}")
        print(f"⏱️  Time: {result['time']:.2f}s")
        print(f"🔢 Tokens: {result['tokens']}")
    
    print("\n2. Testing HuggingFace (if you have API key):")
    print("-" * 50)
    hf_key = input("Enter HuggingFace API key (or press Enter to skip): ").strip()
    
    if hf_key:
        hf_caller = LLMCaller("hf-mistral", hf_key)
        result = hf_caller.call(test_prompt)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Response: {result['response']}")
            print(f"⏱️  Time: {result['time']:.2f}s")
            print(f"🔢 Tokens: {result['tokens']}")
    else:
        print("⏭️  Skipped HuggingFace test")
    
    print("\n" + "="*80)
    print("SETUP INSTRUCTIONS:")
    print("="*80)
    print("""
1. OLLAMA (100% Free, Runs Locally) - RECOMMENDED:
   ✓ Install: curl -fsSL https://ollama.com/install.sh | sh
   ✓ Run: ollama run llama3.2
   ✓ No API key needed!
   ✓ Fast and private

2. HUGGINGFACE (Free Cloud API):
   ✓ Sign up: https://huggingface.co
   ✓ Get token: https://huggingface.co/settings/tokens
   ✓ Free but has rate limits
   ✓ Models: Phi-3-mini, Qwen2.5

Available Models:
  • ollama-llama  → Llama 3.2 (Local)
  • hf-mistral    → Phi-3-mini (Cloud)
  • hf-gemma      → Qwen2.5 (Cloud)
""")