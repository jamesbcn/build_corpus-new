import os
import json
from openai import OpenAI
from tqdm import tqdm

# --- CONFIGURATION ---
API_KEY = "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"
INPUT_FILENAME = "batch_tasks.jsonl"
TRACKING_FILE = "active_batches.json"

# OpenAI Batch Limit is 50,000 requests per file.
# We use 45,000 to be safe and keep file sizes manageable.
CHUNK_SIZE = 45000 

client = OpenAI(api_key=API_KEY)

def submit_shards():
    print(f"Reading {INPUT_FILENAME}...")
    
    # We will store the IDs of all started jobs here
    active_jobs = []
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            active_jobs = json.load(f)
    
    # Generator to read the big file line by line (memory efficient)
    def file_reader(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                yield line

    lines_buffer = []
    chunk_index = 1
    
    # Estimate total lines for progress bar (optional, might take time to count)
    # We'll just iterate.
    
    print("Starting chunked submission...")
    
    for line in tqdm(file_reader(INPUT_FILENAME), unit="lines"):
        lines_buffer.append(line)
        
        if len(lines_buffer) >= CHUNK_SIZE:
            submit_chunk(lines_buffer, chunk_index, active_jobs)
            lines_buffer = [] # Clear memory
            chunk_index += 1
            
    # Submit specific remainder
    if lines_buffer:
        submit_chunk(lines_buffer, chunk_index, active_jobs)

    print(f"\n--- ALL DONE ---")
    print(f"Submitted {len(active_jobs)} batches.")
    print(f"Tracking IDs saved to '{TRACKING_FILE}'.")

def submit_chunk(lines, index, active_jobs):
    chunk_filename = f"temp_chunk_{index}.jsonl"
    
    # 1. Write the temporary chunk file
    with open(chunk_filename, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    try:
        # 2. Upload File
        print(f"\nChunk {index}: Uploading {len(lines)} requests...")
        with open(chunk_filename, 'rb') as f:
            batch_file = client.files.create(file=f, purpose="batch")
        
        # 3. Create Batch Job
        print(f"Chunk {index}: Starting Job...")
        batch_job = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h"
        )
        
        # 4. Log it
        job_info = {
            "chunk": index,
            "batch_id": batch_job.id,
            "file_id": batch_file.id,
            "status": "submitted",
            "timestamp": batch_job.created_at
        }
        active_jobs.append(job_info)
        
        # Save tracking file immediately just in case script crashes
        with open(TRACKING_FILE, 'w') as f:
            json.dump(active_jobs, f, indent=2)
            
        print(f"Chunk {index}: SUCCESS (ID: {batch_job.id})")

    except Exception as e:
        print(f"Chunk {index}: FAILED - {e}")
    
    finally:
        # Cleanup temp file
        if os.path.exists(chunk_filename):
            os.remove(chunk_filename)

if __name__ == "__main__":
    submit_shards()