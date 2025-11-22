from openai import OpenAI
import sys

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434/v1"
MODEL_NAME = "llama3"  # Ensure you have pulled this model ('ollama pull llama3')

def test_connection():
    print(f"1. Connecting to Ollama at {OLLAMA_URL}...")
    
    client = OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama" # Required but ignored
    )

    try:
        print(f"2. Sending test message to '{MODEL_NAME}'...")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test connection. Reply with the single word 'Success'."}
            ],
            max_tokens=10
        )
        
        answer = response.choices[0].message.content.strip()
        print(f"\n✅ SUCCESS! Ollama replied: '{answer}'")
        print("You are ready to run 'regrade_corpus_with_ai.py'")

    except Exception as e:
        print(f"\n❌ FAILED to connect.")
        print(f"Error details: {e}")
        print("\nTROUBLESHOOTING:")
        print("1. Is Ollama running? (Run 'ollama serve' in a separate terminal)")
        print(f"2. Do you have the model? (Run 'ollama pull {MODEL_NAME}')")
        print("3. Is the URL correct? (Default is http://localhost:11434/v1)")

if __name__ == "__main__":
    test_connection()