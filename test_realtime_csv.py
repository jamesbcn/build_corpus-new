import pandas as pd
from qwen_sm import analyzer
from diagnostic_dashboard import diagnostic_dashboard

# --- Define the CSV file path ---
CSV_FILE = 'miscategorized.csv'

# --- Read data from the CSV file ---
try:
    df = pd.read_csv(CSV_FILE)
    print(f"Successfully loaded data from {CSV_FILE}. Total rows: {len(df)}")
except FileNotFoundError:
    print(f"Error: The file '{CSV_FILE}' was not found.")
    exit()

# --- Run analyzer on CSV data ---
results = []
predicted_list = []
reasoning_list = []

total_rows = len(df)

for index, row in df.iterrows():
    if 'sentence' in row and 'expected' in row:
        sentence = row["sentence"]
        expected = str(row["expected"])

        predicted, reasoning = analyzer(sentence)

        results.append({
            "sentence": sentence,
            "expected": expected,
            "predicted": predicted,
            "reasoning": reasoning
        })

        predicted_list.append(predicted)
        reasoning_list.append(reasoning)

        print(f"Sentence: {sentence}")
        print(f"Expected: {expected} | Predicted: {predicted}")
        print(f"Reasoning: {reasoning}\n")
        print(f"[{index+1}/{total_rows}] Processing row {index+1}")
    else:
        print(f"Skipping row {index}: Missing 'sentence' or 'expected' column.")
        print(f"[{index+1}/{total_rows}] Processing row {index+1}")
        predicted_list.append(None)
        reasoning_list.append(None)

# --- Add predictions and reasoning to DataFrame ---
df["predicted"] = predicted_list
df["reasoning"] = reasoning_list

# --- Filter mismatches only ---
mismatches = df[df["expected"] != df["predicted"]]

# --- Save mismatches to new CSV ---
mismatches.to_csv("mismatches_only.csv", index=False)
print(f"\nSaved mismatches only to 'mismatches_only.csv'. Total mismatches: {len(mismatches)}")

# --- Evaluate ---
print("\n--- Running Diagnostic Dashboard ---")
if results:
    diagnostic_dashboard(results, results)
else:
    print("No results to evaluate. Check the CSV file content.")
