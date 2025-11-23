import pandas as pd
from qwen import analyzer
from diagnostic_dashboard import diagnostic_dashboard

# --- Tiny test set ---
test_sentences = [
    {"sentence": "Tengo un gato.", "expected": "A1"},
    {"sentence": "Aunque estaba cansado, terminé el proyecto.", "expected": "B2"},
    {"sentence": "Si hubiera tenido más tiempo, habría viajado a Italia.", "expected": "C1"},
    {"sentence": "La epistemología cuestiona los fundamentos del conocimiento humano.", "expected": "C2"},
]

# --- Run analyzer ---
results = []
for row in test_sentences:
    predicted, reasoning = analyzer(row["sentence"])
    results.append({
        "sentence": row["sentence"],
        "expected": row["expected"],
        "predicted": predicted,
        "reasoning": reasoning
    })
    print(f"Sentence: {row['sentence']}")
    print(f"Expected: {row['expected']} | Predicted: {predicted}")
    print(f"Reasoning: {reasoning}\n")

# --- Evaluate ---
diagnostic_dashboard(results, results)