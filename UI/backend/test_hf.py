# backend/test_hf_simple.py
"""
Simple test script specifically for HuggingFace models.
Use this to test your HF token!
"""

from llm_caller import LLMCaller
import time

print("="*70)
print("  HUGGINGFACE MODEL TESTER")
print("="*70)

# Step 1: Get token
print("\n📝 Step 1: Enter your HuggingFace token")
print("   (Get it from: https://huggingface.co/settings/tokens)")
print("   (Should start with 'hf_')")
hf_token = input("\n🔑 Paste your HuggingFace token here: ").strip()

if not hf_token:
    print("❌ No token provided. Exiting...")
    exit()

if not hf_token.startswith("hf_"):
    print("⚠️  Warning: Token should start with 'hf_'")
    print("   Are you sure this is a HuggingFace token?")
    confirm = input("   Continue anyway? (y/n): ")
    if confirm.lower() != 'y':
        exit()

# Step 2: Choose model
print("\n🤖 Step 2: Choose a model")
print("   1. hf-mistral (Mistral 7B - Recommended)")
print("   2. hf-gemma (Gemma 2B - Faster but smaller)")

choice = input("\nEnter 1 or 2 (default: 1): ").strip()
model_name = "hf-gemma" if choice == "2" else "hf-mistral"

print(f"\n✅ Selected: {model_name}")

# Step 3: Test with simple prompt
print("\n🧪 Step 3: Testing API call...")
print("   This may take 20-60 seconds on first try (model loading)")
print("   Please be patient! ⏳")

test_prompt = """Based on this data, which flight has the worst delay?

Flight UA123: avg delay = 45.2 minutes
Flight AA456: avg delay = 12.5 minutes

Answer in one short sentence."""

caller = LLMCaller("hf-gemma", hf_token)

print(f"\n⏳ Calling {model_name}...")
start = time.time()

result = caller.call(test_prompt, max_tokens=100, temperature=0.1)

elapsed = time.time() - start

print("\n" + "="*70)
print("  RESULTS")
print("="*70)

if "error" in result:
    print(f"\n❌ ERROR: {result['error']}")
    print("\n📋 Common issues:")
    print("   • Token is invalid → Create new token")
    print("   • Model is loading → Wait 1 minute and try again")
    print("   • Rate limit → Wait a few minutes")
    print("   • Network issue → Check internet connection")
else:
    print(f"\n✅ SUCCESS! (took {elapsed:.2f} seconds)")
    print(f"\n🤖 Model: {model_name}")
    print(f"⏱️  Response Time: {result['time']:.2f}s")
    print(f"📊 Tokens: {result.get('tokens', 'N/A')}")
    print(f"\n💬 Response:")
    print("-" * 70)
    print(result['response'])
    print("-" * 70)
    
    print("\n🎉 Your HuggingFace token is working!")
    print("\n📝 Next steps:")
    print("   1. Save this token securely (don't share it!)")
    print("   2. Run: python -m streamlit run ../ui/streamlit_app.py")
    print("   3. Select model: " + model_name)
    print("   4. Enter your token in the sidebar")
    print("   5. Try asking questions about flights!")

print("\n" + "="*70)