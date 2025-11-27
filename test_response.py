from qwen_sm import analyzer  # replace with your actual module name

# Example Spanish sentence
spanish_sentence = "Creo que mañana hará sol"

# Call the analyzer
level, explanation = analyzer(spanish_sentence)

# Print the full raw output
print("----- FULL RAW ANALYZER RESPONSE -----")
print("Level:", level)
print("Reasoning:", explanation)
print("--------------------------------------")