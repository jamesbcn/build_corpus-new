import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix

# Load your evaluation results
df = pd.read_csv("miscategorized.csv")  # columns: sentence, expected, predicted

# Classification report
report = classification_report(df["expected"], df["predicted"],
                               labels=["A1","A2","B1","B2","C2"],
                               output_dict=True)
report_df = pd.DataFrame(report).transpose()

# Confusion matrix
cm = confusion_matrix(df["expected"], df["predicted"], labels=["A1","A2","B1","B2","C2"])

# --- Confusion Matrix Heatmap ---
plt.figure(figsize=(6,5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["A1","A2","B1","B2","C2"],
            yticklabels=["A1","A2","B1","B2","C2"])
plt.title("Confusion Matrix")
plt.xlabel("Predicted")
plt.ylabel("Expected")
plt.tight_layout()
plt.savefig("confusion_matrix.png")   # automatically saves
plt.close()

# --- Precision/Recall/F1 Bar Chart ---
metrics = ["precision","recall","f1-score"]
report_df.loc[["A1","A2","B1","B2","C2"], metrics].plot(kind="bar", figsize=(8,6))
plt.title("Per-Level Precision, Recall, F1")
plt.xticks(rotation=0)
plt.ylabel("Score")
plt.ylim(0,1)
plt.tight_layout()
plt.savefig("metrics_bar_chart.png")  # automatically saves
plt.close()
