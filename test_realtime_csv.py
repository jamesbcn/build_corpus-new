import pandas as pd
from qwen_sm import analyzer
from diagnostic_dashboard import diagnostic_dashboard

# --- Define the CSV file path ---
CSV_FILE = 'miscategorized.csv'

# --- Read data from the CSV file ---
# Assuming miscategorized.csv has columns 'sentence' (text) and 'expected' (A1, B2, C1, etc.)
try:
    df = pd.read_csv(CSV_FILE)
    print(f"Successfully loaded data from {CSV_FILE}. Total rows: {len(df)}")
except FileNotFoundError:
    print(f"Error: The file '{CSV_FILE}' was not found.")
    exit() # Exit the script if the file is not found

# --- Run analyzer on CSV data ---
results = []
# Iterate over DataFrame rows using iterrows()
for index, row in df.iterrows():
    # Ensure columns exist before accessing them
    if 'sentence' in row and 'expected' in row:
        sentence = row["sentence"]
        expected = str(row["expected"]) # Ensure 'expected' is treated as a string

        # Run the analyzer function
        predicted, reasoning = analyzer(sentence)

        # Append results
        results.append({
            "sentence": sentence,
            "expected": expected,
            "predicted": predicted,
            "reasoning": reasoning
        })

        # Print output to console
        print(f"Sentence: {sentence}")
        print(f"Expected: {expected} | Predicted: {predicted}")
        print(f"Reasoning: {reasoning}\n")
    else:
        print(f"Skipping row {index}: Missing 'sentence' or 'expected' column.")


# --- Evaluate ---
# The diagnostic_dashboard typically takes the list of results for evaluation
print("\n--- Running Diagnostic Dashboard ---")
if results:
    # Passing 'results' twice, as it is the standard practice when the input data
    # and the results data are derived from the same list/source in this pattern.
    diagnostic_dashboard(results, results)
else:
    print("No results to evaluate. Check the CSV file content.")