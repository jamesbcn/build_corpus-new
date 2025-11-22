from groq_client import analyzer  # replace with your actual module name

# Example Spanish sentence
spanish_sentence = "Cuanto antes, mejor."

# Call the analyzer
raw_response = analyzer(spanish_sentence)

# Print the full raw output
print("----- FULL RAW ANALYZER RESPONSE -----")
print(raw_response)
print("--------------------------------------")