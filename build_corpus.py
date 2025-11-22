import os
import time
from openai import OpenAI

# --- CONFIGURATION ---
# PASTE YOUR KEY HERE if you aren't using environment variables:
API_KEY = "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" 
FILENAME = "batch_tasks.jsonl"

client = OpenAI(api_key=API_KEY)

def submit_job():
    print(f"1. Uploading '{FILENAME}' to OpenAI (this may take a minute)...")
    
    # Upload file with 'batch' purpose
    with open(FILENAME, "rb") as f:
        batch_file = client.files.create(
            file=f,
            purpose="batch"
        )
    
    file_id = batch_file.id
    print(f"   File Uploaded! ID: {file_id}")
    
    print("2. Creating Batch Job...")
    batch_job = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h" # This triggers the 50% discount
    )
    
    print("\n--- BATCH JOB STARTED ---")
    print(f"Batch ID: {batch_job.id}")
    print(f"Status:   {batch_job.status}")
    print("-------------------------")
    print("OpenAI will now process this in the background.")
    print("It typically takes 6-12 hours for large batches, but up to 24h.")
    print("\nSave your Batch ID! You will need it to download the results tomorrow.")

if __name__ == "__main__":
    submit_job()