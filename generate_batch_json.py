import json
from pymongo import MongoClient
from tqdm import tqdm

# --- CONFIGURATION ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "language_learning"
COLLECTION_NAME = "english_sentences"
OUTPUT_FILENAME = "batch_tasks.jsonl"

# --- THE AI PROMPT ---
# Explicitly tells the AI that the length is provided and to ignore names
# SYSTEM_PROMPT = (
#     "You are an expert linguist. Rate the difficulty for a NATIVE ENGLISH SPEAKER "
#     "to translate this sentence INTO SPANISH on a scale of 1-10 (1=Basic, 10=Literary/Archaic). "
#     "Criteria: Sentence length, vocabulary rarity, grammatical complexity, and idiomatic usage. "
#     "Do not increase difficulty for proper nouns or names, even if uncommon. "
#     "Return ONLY the integer (e.g. 7)."
# )
SYSTEM_PROMPT = (
    "You are an expert linguist grading English sentences for translation into Spanish. "
    "Assign a difficulty score (1-10) using the following GRAMMATICAL GUIDELINES as a primary reference:\n\n"
    "GUIDELINES:\n"
    "1: NO VERBS. Nouns/Adjectives only (e.g., 'The red car', 'Hello').\n"
    "2: SIMPLE PRESENT. Subject-Verb-Object (e.g., 'I eat apples').\n"
    "3: SIMPLE PAST / FUTURE. (e.g., 'I walked', 'I will go').\n"
    "4: PERFECT TENSES. (Have + Participle).\n"
    "5: COMMANDS / IMPERATIVE. Complex in Spanish due to negative/affirmative shifts & pronoun placement.\n"
    "6: PASSIVE VOICE / GERUNDS. (e.g., 'It was made', 'Swimming is fun').\n"
    "7: PRESENT SUBJUNCTIVE. (Triggers: Want/Hope/Doubt + 'that').\n"
    "8: CONDITIONAL / PAST SUBJUNCTIVE. (e.g., 'I would go', 'If I were you').\n"
    "9: COMPOUND COMPLEX / IDIOMS. Multiple clauses, idiomatic phrasal verbs.\n"
    "10: LITERARY / ARCHAIC. (e.g., 'Lest we forget', 'Thou art').\n\n"
    "CONSIDERATIONS:\n"
    "- PROPER NOUNS do not increase difficulty.\n"
    "- COGNATES reduce difficulty by 1 point.\n"
    "- Return ONLY the integer."
)

def generate_jsonl():
    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    
    total_count = collection.count_documents({})
    print(f"Found {total_count} sentences. Generating batch file...")
    
    # Fetch 'word_count' along with text
    cursor = collection.find({}, {"_id": 1, "text": 1, "word_count": 1})
    
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        for doc in tqdm(cursor, total=total_count, unit="req"):
            
            # Fallback if word_count is missing
            w_count = doc.get("word_count", len(doc["text"].split()))
            
            # Format the user content to include the explicit count
            user_content = f"Word Count: {w_count}\nSentence: {doc['text']}"
            
            # Construct the OpenAI Batch Request Object
            request_object = {
                "custom_id": str(doc["_id"]), # Maps result back to Mongo ID
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content}
                    ],
                    "max_tokens": 5,     
                    "temperature": 0.0   
                }
            }
            
            # Write as one line of JSON
            f.write(json.dumps(request_object) + "\n")

    print(f"\nSuccess! File '{OUTPUT_FILENAME}' created.")
    print("Next step: Run 'submit_batch_job.py' to send this to OpenAI.")

if __name__ == "__main__":
    generate_jsonl()