import os
import time
import re
from pymongo import MongoClient
from tqdm import tqdm
from openai import OpenAI

# --- CONFIGURATION ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "language_learning"
COLLECTION_NAME = "english_sentences"
SAMPLE_SIZE = 120  # <<<--- TESTING ONLY: Using a very small sample size for gpt-4o
                                  # Remember to increase this back to 1000 for gpt-4o-mini runs!

# PASTE KEY HERE if not in environment variables
API_KEY = "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"

client = OpenAI(api_key=API_KEY)

# --- PROMPT (v39: Hard-Coding Tener/Ser Conflict) ---
SYSTEM_PROMPT = (
    "You are an expert Spanish teacher. Your task is to rate the difficulty of translating the English sentence provided into natural, correct Spanish on a scale of 1 to 10. Your response MUST include reasoning.\n"
    "\n--- CORE GRAMMAR SCORING FRAMEWORK ---\n"
    "A1: Simple Present (Regular Verbs), Ser/Estar/Tener/Ir. **NEVER PAST TENSE**. Score 1-2 (length may bump +1)\n"
    "A2: Past Tenses (Perfecto), Obligation (Tener que), Near Future (Ir a). Score 3-4\n"
    "B1-B2: Indefinido vs Imperfecto, Future/Conditional, Commands, Subjunctive, Reverse Verbs. Score 5-6\n"
    "C1+: Imperfect Subjunctive, Passive Se, Advanced Idioms. Score 7+\n"
    "--- NON-NEGOTIABLE SCORE RULES ---\n"
    "**Tener Switch**: AT LEAST 2 (age, states)\n"
    "**Irregular Present Verb**: AT LEAST 3\n"
    "**Obligation/Near Future**: Tener que = 4; Ir a = 3 unless irregular/subordinate\n"
    "**Commands/Subordinate Clauses**: Simple subordinate (indicative) = 4; Imperative/subjunctive = 5+\n"
    "**Reverse Verbs**: Basic (gustar/doler) = 3; nuanced (encantar/faltar/quedar) = 4+\n"
    "**Advanced Idioms**: AT LEAST 8\n"
    "\n"
    "INSTRUCTIONS:\n"
    "1. The analysis MUST be **no more than two sentences** long.\n"
    "2. Prioritize the highest grammatical complexity found.\n"
    "3. Format your response EXACTLY like this:\n"
    "Analysis: <brief grammatical explanation stating the highest rule triggered>\n"
    "Score: <integer>"
)

def extract_score(content):
    """Robustly finds 'Score: X' at the end of the response."""
    # Find 'Score: [1-10]'
    match = re.search(r'Score:\s*([1-9]|10)', content, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Fallback to find any integer at the end (less reliable)
    numbers = re.findall(r'\b([1-9]|10)\b', content)
    if numbers:
        return int(numbers[-1])
        
    return None

def reset_database(collection):
    """
    OPTIONAL: Wipes all existing ratings so we can start fresh.
    """
    print("⚠️  Clearing ALL difficulty ratings...")
    result = collection.update_many(
        {}, 
        {"$unset": {"difficulty_rating": "", "ai_explanation": ""}}
    )
    print(f"Reset complete. Modified {result.modified_count} documents.")

def regrade_database():
    # Connect to DB
    mongo_client = MongoClient(MONGO_URI)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]
    
    # --- RESET STEP (Run this ONCE) ---
    # Uncomment the line below if you want to wipe all scores before starting
    # reset_database(collection)
    
    # Find documents that have NO rating yet
    #query = {"difficulty_rating": {"$exists": False}}
    query = {"difficulty_rating": 5}
    #query = {"_id": {"$in": [1317, 1330, 1332, 1425, 1435, 1445, 1471, 1473, 1561, 1611, 1647, 1686, 1687]}}
    
    total_unrated = collection.count_documents(query)
    limit = min(total_unrated, SAMPLE_SIZE)
    
    if limit == 0:
        print("No unrated sentences found! Did you mean to uncomment 'reset_database'?")
        return

    print(f"Found {total_unrated} unrated sentences. Processing {limit} of them live using gpt-4o...")
    
    # Fetch the docs
    cursor = collection.find(query, {"_id": 1, "text": 1, "word_count": 1}).limit(limit)
    
    count = 0
    
    for doc in tqdm(cursor, total=limit, unit="req"):
        try:
            # Prepare Input (User query is just the sentence)
            user_content = doc["text"]
            
            # Call OpenAI (Live Request)
            response = client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT }, 
                    {"role": "user", "content": user_content}
                ],
                max_tokens=150, # Sufficient for Analysis
                temperature=0.0
            )
            
            # Extract Score
            content = response.choices[0].message.content.strip()
            new_score = extract_score(content)
            
            # Verify it's a number
            if new_score is not None:
                
                # Update MongoDB with both the score and the full explanation
                collection.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "difficulty_rating": new_score,
                            "ai_explanation": content # Save the full Analysis and Score text
                        }
                    }
                )
                count += 1
            else:
                # Log the raw junk output for manual review
                collection.update_one(
                    {"_id": doc["_id"]},
                    {
                        "$set": {
                            "difficulty_rating": 0,
                            "ai_explanation": f"FAILED TO PARSE: {content}"
                        }
                    }
                )
                print(f"\nSkipping ID {doc['_id']}: AI returned unparseable content.")
                
        except Exception as e:
            # Log and pause on errors
            print(f"\nError on ID {doc['_id']}: {e}")
            time.sleep(1)

    print(f"\nSuccess! Updated {count} sentences with AI scores and explanations.")

if __name__ == "__main__":
    regrade_database()