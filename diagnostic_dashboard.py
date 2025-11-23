# diagnostic_dashboard.py

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from collections import Counter
from qwen import analyzer   

# --- Dashboard function ---
def diagnostic_dashboard(test_results, import_results, levels=("A1","A2","B1","B2","C1","C2","UNKNOWN")):
    # Overall accuracy
    harness_correct = sum(1 for r in test_results if r["predicted"] == r["expected"])
    import_correct = sum(1 for r in import_results if r["predicted"] == r["expected"])
    unknowns = sum(1 for r in import_results if r["predicted"] == "UNKNOWN")

    print(f"Harness Accuracy: {harness_correct}/{len(test_results)} = {harness_correct/len(test_results):.2%}")
    print(f"Import Accuracy:  {import_correct}/{len(import_results)} = {import_correct/len(import_results):.2%}")
    print(f"Unknowns: {unknowns}/{len(import_results)} = {unknowns/len(import_results):.2%}")

    # Confusion matrix (numeric)
    matrix = {exp: Counter() for exp in levels}
    for r in import_results:
        exp, pred = r["expected"], r["predicted"]
        if exp in matrix:
            matrix[exp][pred] += 1

    print("\nConfusion Matrix:")
    header = "Expected\\Pred".ljust(12) + "".join(l.ljust(9) for l in levels)
    print(header)
    for exp in levels:
        row = exp.ljust(12)
        for pred in levels:
            row += str(matrix[exp][pred]).ljust(9)
        print(row)

    # Per-level accuracy
    print("\nPer-Level Accuracy:")
    for level in levels:
        subset = [r for r in import_results if r["expected"] == level]
        if not subset:
            continue
        correct = sum(1 for r in subset if r["predicted"] == level)
        total = len(subset)
        print(f"{level}: {correct}/{total} = {correct/total:.2%}")

    # Bar chart
    accuracies = []
    for level in levels:
        subset = [r for r in import_results if r["expected"] == level]
        if not subset:
            accuracies.append(0)
            continue
        correct = sum(1 for r in subset if r["predicted"] == level)
        total = len(subset)
        accuracies.append(correct/total)

    plt.figure(figsize=(9,5))
    plt.bar(levels, accuracies, color="skyblue")
    plt.ylim(0,1)
    plt.title("Per-Level Accuracy (including UNKNOWN)")
    plt.ylabel("Accuracy")
    plt.xlabel("CEFR Level")
    plt.show()

    # Heatmap
    df = pd.DataFrame(matrix).T.fillna(0).astype(int)
    df = df.reindex(index=levels, columns=levels).fillna(0).astype(int)

    plt.figure(figsize=(9,6))
    sns.heatmap(df, annot=True, fmt="d", cmap="Blues", cbar=True)
    plt.title("Confusion Matrix Heatmap (including UNKNOWN)")
    plt.xlabel("Predicted")
    plt.ylabel("Expected")
    plt.show()


if __name__ == "__main__":
    # --- Load your misclassified shard ---
    df = pd.read_csv("miscategorized.csv")  # file with sentence,expected

    # Run analyzer on each sentence
    # Replace `your_model_predict` with your actual inference call
    df[["predicted", "reasoning"]] = df["sentence"].apply(lambda s: pd.Series(analyzer(s)))
    
    # Save back to CSV so diagnostic_dashboard can read it
    df.to_csv("miscategorized.csv", index=False)
    print("Updated miscategorized.csv with predictions.")

    # Convert to list of dicts
    import_results = df.to_dict(orient="records")

    # For harness comparison, you can reuse import_results or load another dataset
    test_results = import_results

    # Run dashboard
    diagnostic_dashboard(test_results, import_results)
