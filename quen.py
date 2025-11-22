import os
import json
import csv
from datetime import datetime
from collections import Counter
from pymongo import MongoClient
from tqdm import tqdm
from openai import OpenAI


OLLAMA_URL = "http://localhost:11434/v1"
MODEL_NAME = "qwen2.5:14b"  

# --- USER PROMPTS ---
try:
    SAMPLE_SIZE = int(input("Enter sample size (e.g., 1000): ").strip())
except ValueError:
    SAMPLE_SIZE = 1000
    print("⚠️ Invalid input, defaulting SAMPLE_SIZE to 1000.")

empty_choice = input("Do you want to wipe all AI ratings before regrading? (yes/no): ").strip().lower()
EMPTY_COLLECTION = empty_choice in ["yes", "y", "true", "1"]

print(f"✅ SAMPLE_SIZE set to {SAMPLE_SIZE}")
print(f"✅ EMPTY_COLLECTION set to {EMPTY_COLLECTION}")

# --- CONFIGURATION ---
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "language_learning"
COLLECTION_NAME = "english_sentences"

# --- SETUP ---
client = OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama" # Required but ignored
    )

TRANSLATOR_MODEL = MODEL_NAME
ANALYZER_MODEL = MODEL_NAME

# --- CEFR Mapping ---
CEFR_MAP = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

def translator(english_sentence: str) -> str:
    """Translate English → Spanish using llama3."""
    response = client.chat.completions.create(
        model=TRANSLATOR_MODEL,
        messages=[
            {"role": "system", "content": "Translate the following English sentence into natural, fluent Spanish. Output only the Spanish sentence."},
            {"role": "user", "content": english_sentence}
        ],
        max_completion_tokens=100,
        temperature=0.0
    )
    return response.choices[0].message.content.strip()

def analyzer(spanish_sentence: str) -> str:
    """Classify Spanish sentence by CEFR level with expanded anchors and contrastive pairs."""
    response = client.chat.completions.create(
        model=ANALYZER_MODEL,
        messages=[
            {"role": "system", "content": (
                "Classify the following Spanish sentence by CEFR level (A1, A2, B1, B2, C1, C2). "
                "Guidelines: "
                "A1 = simple present tense with basic vocabulary. "
                "A2 = idiomatic expressions (tener hambre, tener frío), habitual actions, modal verbs (tener que, poder, necesitar, querer), preference verbs (gustar, encantar). "
                "B1 = past and future tenses, present perfect, everyday reasoning. "
                "B2 = sentences with connectors (aunque, sin embargo, mientras, cuando) OR multiple independent clauses joined by punctuation (semicolon, colon, dash), and subjunctive in common contexts (es posible que, prefiero que). "
                "C1 = complex conditionals, nuanced subjunctive, advanced connectors. "
                "C2 = abstract, academic, or philosophical sentences, even if expressed in simple present tense. "
                "Classify at the highest CEFR level indicated by the grammar or vocabulary present. "
                "Sentences containing idioms, connectors, modal verbs, or academic language should not be treated as A1."
            )},

            # --- A1 anchors ---
            {"role": "user", "content": "Tengo un gato."}, {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Ella vive en Madrid."}, {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Mi casa es pequeña."}, {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "El libro está en la mesa."}, {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Él come una manzana."}, {"role": "assistant", "content": "A1"},

            # --- A2 anchors ---
            {"role": "user", "content": "Tengo que limpiar mi habitación."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Tengo hambre después de correr."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Tengo frío en invierno."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Voy al supermercado cada sábado."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Me gusta bailar salsa."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "¿Puedes ayudarme con la tarea?"}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Necesito comprar un regalo."}, {"role": "assistant", "content": "A2"},
            {"role": "user", "content": "Quiero aprender a tocar la guitarra."}, {"role": "assistant", "content": "A2"},

            # --- B1 anchors ---
            {"role": "user", "content": "Ayer fui al cine con mis amigos."}, {"role": "assistant", "content": "B1"},
            {"role": "user", "content": "Mañana visitaré a mis abuelos."}, {"role": "assistant", "content": "B1"},
            {"role": "user", "content": "He terminado mi tarea."}, {"role": "assistant", "content": "B1"},
            {"role": "user", "content": "Este es el pueblo del que te hablé."}, {"role": "assistant", "content": "B1"},
            {"role": "user", "content": "Comí caviar por primera vez."}, {"role": "assistant", "content": "B1"},

            # --- B2 anchors ---
            {"role": "user", "content": "Aunque estaba cansado, terminé el proyecto."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Prefiero que vengas temprano."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Es posible que llueva mañana."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Sin embargo, decidimos continuar."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Cuando termine el curso, buscaré trabajo."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "No abras antes de que el tren se detenga."}, {"role": "assistant", "content": "B2"},

            # --- New idiomatic/discourse anchors ---
            {"role": "user", "content": "No te puedes perder; está justo en el centro."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Es fácil encontrarlo; hay señales por todas partes."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "No cabe duda; la ciudad ofrece muchas oportunidades."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "Lo más probable es que llegues a tiempo; el tren suele ser puntual."}, {"role": "assistant", "content": "B2"},
            {"role": "user", "content": "No te preocupes; siempre hay alguien dispuesto a ayudar."}, {"role": "assistant", "content": "B2"},

            # --- C2 anchors ---
            {"role": "user", "content": "La epistemología cuestiona los fundamentos del conocimiento humano."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La literatura posmoderna refleja la fragmentación de la identidad contemporánea."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La ontología estudia la naturaleza del ser y la existencia."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La segunda mitad de la vida de un hombre está compuesta únicamente por los hábitos que ha adquirido durante la primera mitad."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "Estoy en contra de usar la muerte como castigo. También estoy en contra de usarla como recompensa."}, {"role": "assistant", "content": "C2"},

            # --- New academic/abstract anchors ---
            {"role": "user", "content": "Las personas ciegas a veces desarrollan una habilidad compensatoria para percibir la proximidad de los objetos que las rodean."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La neurociencia analiza cómo el cerebro procesa estímulos externos."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La ética examina las normas que regulan la conducta humana."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La sociología estudia las estructuras y dinámicas de las sociedades modernas."}, {"role": "assistant", "content": "C2"},
            {"role": "user", "content": "La filosofía política reflexiona sobre la legitimidad del poder y la justicia social."}, {"role": "assistant", "content": "C2"},
                
            # --- Actual request ---
            {"role": "user", "content": spanish_sentence}
        ],
        temperature=0.8,
        top_p=1.0,
        stream=False,
        max_completion_tokens=1000,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "cefr_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "cefr_level": {
                            "type": "string",
                            "enum": ["A1", "A2", "B1", "B2", "C1", "C2"]
                        }
                    },
                    "required": ["cefr_level"]
                }
            }
        }
    )

    raw_output = response.choices[0].message.content.strip()

     # 2. Load the JSON
    data = json.loads(raw_output)

    # 3. Access the CEFR level property
    cefr_level = data.get("cefr_level") 
    
    print(f"✅ CEFR level: {cefr_level}")
    return cefr_level


def package_result(english_sentence: str) -> dict:
    spanish = translator(english_sentence)
    cefr = analyzer(spanish)
    cefr_val = CEFR_MAP.get(cefr, 0)
    return {"translation": spanish, "cefr_level": cefr, "cefr_value": cefr_val}

def reset_ai_ratings(collection):
    confirm = input("⚠️ Are you sure you want to wipe ALL AI ratings (yes/no)? ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("❌ Reset cancelled.")
        return
    print("⚠️ Resetting all AI-generated fields...")
    result = collection.update_many({}, {"$unset": {
        "translation": "", "cefr_level": "", "cefr_value": "", "ai_model": "", "updated_at": ""
    }})
    print(f"✅ Reset complete. Removed AI ratings from {result.modified_count} documents.")

def report_results(collection, query=None):
    if query is None:
        query = {"cefr_level": {"$exists": True}}
    cursor = collection.find(query, {"cefr_level": 1, "translation": 1})
    levels = [doc.get("cefr_level", "UNKNOWN") for doc in cursor]
    counts = Counter(levels)
    print("\n📊 CEFR Classification Report")
    for level in ["A1", "A2", "B1", "B2", "C1", "C2", "UNKNOWN"]:
        print(f"{level}: {counts.get(level, 0)}")
    total = sum(counts.values())
    print(f"\nTotal classified sentences: {total}")
    if counts.get("UNKNOWN", 0) > 0:
        print("⚠️ Some sentences were marked UNKNOWN — review raw outputs for drift.")

def test_harness(export_csv=False, csv_path="harness_results.csv"):
    test_cases = [
        ("Tengo un gato.", "A1"), 
        ("Ella vive en Madrid.", "A1"),
        ("Comemos pan.", "A1"),
        ("Mi hermano trabaja en una oficina.", "A1"),
        ("Los niños juegan en el parque.", "A1"),
        ("Estudio español todos los días.", "A1"),
        ("Bebo agua.", "A1"),
        ("Ellos leen un libro.", "A1"),
        ("Nosotros cantamos una canción.", "A1"),
        ("El perro corre rápido.", "A1"),

        # --- A2: idioms, modal, reversal verbs ---
        ("Tengo que limpiar mi habitación.", "A2"),
        ("Me gusta bailar salsa.", "A2"),
        ("Tengo frío en invierno.", "A2"),
        ("Nos encanta viajar en verano.", "A2"),
        ("¿Puedes ayudarme con la tarea?", "A2"),
        ("Voy al supermercado cada sábado.", "A2"),
        ("Necesito comprar un regalo.", "A2"),
        ("Quiero aprender a tocar la guitarra.", "A2"),
        ("Me duele la cabeza.", "A2"),
        ("Prefiero comer pizza.", "A2"),

        # --- B1: past/future ---
        ("Ayer fui al cine con mis amigos.", "B1"),
        ("Mañana visitaré a mis abuelos.", "B1"),
        ("Estudié mucho para el examen.", "B1"),
        ("Compraré un coche el próximo año.", "B1"),
        ("Si estudio más, aprobaré el curso.", "B1"),
        ("El verano pasado viajamos a Italia.", "B1"),
        ("Cuando era niño, jugaba al fútbol.", "B1"),
        ("El mes que viene empezaré un nuevo trabajo.", "B1"),
        ("He terminado mi tarea.", "B1"),
        ("Si llueve, no iremos al parque.", "B1"),

        # --- B2: connectors, subjunctive ---
        ("Aunque estaba cansado, terminé el proyecto.", "B2"),
        ("Prefiero que vengas temprano.", "B2"),
        ("Sin embargo, decidimos continuar.", "B2"),
        ("Mientras trabajaba, escuchaba música.", "B2"),
        ("Es posible que llueva mañana.", "B2"),
        ("Quiero que me expliques la situación.", "B2"),
        ("Aunque no me gusta, lo haré.", "B2"),
        ("Es mejor que estudies ahora.", "B2"),
        ("No creo que sea verdad.", "B2"),
        ("Cuando termine el curso, buscaré trabajo.", "B2"),

        # --- C1: complex conditionals, nuanced ---
        ("Si hubiera tenido más tiempo, habría viajado a Italia.", "C1"),
        ("Es probable que hubiera ocurrido de otra manera.", "C1"),
        ("De haberlo sabido, habría actuado distinto.", "C1"),
        ("Aunque me lo hubieras pedido, no habría aceptado.", "C1"),
        ("El hecho de que lo hiciera demuestra su compromiso.", "C1"),
        ("Si hubieras estudiado más, habrías aprobado fácilmente.", "C1"),
        ("Es posible que hubiera sido diferente si lo intentaras.", "C1"),

        # --- C2: abstract, academic ---
        ("La globalización ha generado una interdependencia económica sin precedentes.", "C2"),
        ("La epistemología cuestiona los fundamentos del conocimiento humano.", "C2"),
        ("El paradigma científico se transformó radicalmente tras la revolución cuántica.", "C2"),
        ("La literatura posmoderna refleja la fragmentación de la identidad contemporánea.", "C2"),
        ("La semiótica analiza los signos y su interpretación cultural.", "C2"),
        ("La hermenéutica explora la interpretación de los textos en contextos históricos.", "C2"),
        ("La ontología estudia la naturaleza del ser y la existencia.", "C2"),
    ]


    print("\n🔬 Running CEFR Test Harness...\n")
    correct, incorrect = 0, 0
    results = []

    for sentence, expected in test_cases:
        predicted = analyzer(sentence)
        is_correct = (predicted == expected)
        if is_correct:
            correct += 1
        else:
            incorrect += 1

        results.append({"sentence": sentence, "expected": expected, "predicted": predicted, "correct": is_correct})
        print(f"Sentence: {sentence}")
        print(f"Classification: {predicted} | Expected: {expected} | {'✅ Correct' if is_correct else '❌ Incorrect'}\n")

    total = correct + incorrect
    accuracy = (correct / total * 100) if total > 0 else 0

    print("📊 Test Harness Summary")
    print(f"Total cases: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {incorrect}")
    print(f"Accuracy: {accuracy:.1f}%\n")
    
    drift_report(results)

    if export_csv:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["sentence", "expected", "predicted", "correct"])
            writer.writeheader()
            writer.writerows(results)


def drift_report(results):
    """
    Compare predicted vs expected CEFR levels and flag drift.
    Drift = predicted one level lower or higher than expected.
    Also computes drift percentage.
    """
    drift_cases = []
    total = len(results)

    for item in results:
        sentence = item["sentence"]
        expected = item["expected"]
        predicted = item["predicted"]

        if expected in CEFR_MAP and predicted in CEFR_MAP:
            diff = CEFR_MAP[predicted] - CEFR_MAP[expected]
            if abs(diff) == 1:  # one-level drift
                drift_cases.append((sentence, expected, predicted))

    print("\n⚠️ Drift Report")
    if drift_cases:
        for s, e, p in drift_cases:
            print(f"Sentence: {s} | Expected: {e} | Predicted: {p}")
        drift_pct = (len(drift_cases) / total * 100) if total > 0 else 0
        print(f"\nTotal drift cases: {len(drift_cases)}")
        print(f"Drift percentage: {drift_pct:.1f}%")
    else:
        print("No drift detected ✅")


# --- Main Workflow ---
def main():
    mongo_client = MongoClient(MONGO_URI)
    collection = mongo_client[DB_NAME][COLLECTION_NAME]

    if EMPTY_COLLECTION:
        reset_ai_ratings(collection)
        
        
    # Query only for documents that lack a CEFR analysis
    query = {"cefr_level": {"$exists": False}, "text": {"$exists": True}}
    
    # Get total count of documents matching the query (for tqdm total)
    total_to_process = collection.count_documents(query)
    limit = min(total_to_process, SAMPLE_SIZE)
    
    print(f"Starting analysis of {limit} unrated sentences using {TRANSLATOR_MODEL} + {ANALYZER_MODEL}...")

    # Fetch documents based on the calculated limit
    cursor = collection.find(query, {"_id": 1, "text": 1}).limit(limit)

    for doc in tqdm(cursor, total=limit, desc="Processing sentences"):
        try:
            sentence = doc["text"]
            result = package_result(sentence)

            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "translation": result["translation"],
                    "cefr_level": result["cefr_level"],
                    "cefr_value": result["cefr_value"],
                    "ai_model": ANALYZER_MODEL,
                    "updated_at": datetime.utcnow()
                }}
            )
        except Exception as e:
            print(f"\n❌ Error processing ID {doc['_id']}: {e}")
            
    print("✅ Processing complete.")
    report_results(collection)

# --- Entrypoint ---
if __name__ == "__main__":
    # Run harness first to validate tricky cases
    test_harness(export_csv=True)

    # Then run full pipeline if satisfied
    main()
    