import json
import re
import csv
import time
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
DB_NAME = "vocaba"
COLLECTION_NAME = "english"

# --- SETUP ---
client = OpenAI(
        base_url=OLLAMA_URL,
        api_key="ollama" # Required but ignored
    )

TRANSLATOR_MODEL = MODEL_NAME
ANALYZER_MODEL = MODEL_NAME

def translator(english_sentence: str) -> str:
    """Translate English → Spanish using llama3."""
    response = client.chat.completions.create(
        model=TRANSLATOR_MODEL,
        messages=[
            {"role": "system", "content": "Translate the following English sentence into natural, fluent Spanish. Output only the Spanish sentence."},
            {"role": "user", "content": english_sentence}
        ],
        max_completion_tokens=100,
        temperature=0.0,
        reasoning_effort="none",
        stream=False
    )
    return response.choices[0].message.content.strip()

def analyzer(spanish_sentence: str, max_retries: int = 10, pause: float = 0.5):
    """Classify Spanish sentence by CEFR level. Returns ('UNKNOWN','') if parsing fails."""
    valid_levels = {"A1","A2","B1","B2","C1","C2"}
     
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=ANALYZER_MODEL,
                messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an official DELE senior examiner for Instituto Cervantes with 20+ years of experience.\n"
                        "Your task: assign a CEFR level followed by an in-depth justification.\n\n"
                        "Decision rules (strict hierarchical order – never skip):\n"
                        "A1 → exclusively present tense, extremely basic lexicon (saludar, ser/estar, tener for age/family/possession, números, colores). "
                        "Functions limited to introductions, simple possession, location, age. "
                        "No modal verbs (tener que, poder, deber), no idiomatic tener-phrases (hambre, frío, sueño), no periphrastic constructions. "
                        "Discourse limited to isolated sentences or y.\n\n"
                        "A2 → first appearance of pretérito indefinido or perfecto compuesto OR functional expansions: obligation (tener que, deber), ability (poder, saber + inf), "
                        "desire (querer + inf), idiomatic tener-phrases (hambre, frío, sueño). "
                        "Lexicon expands to everyday topics (food, shopping, health, hobbies). "
                        "Discourse includes basic connectors (y, pero, porque, cuando). "
                        "No systematic tense contrast, no subjunctive.\n\n"
                        "B1 → systematic and correct contrast between indefinido and imperfecto. "
                        "Lexicon broadens to narrative vocabulary (childhood, travel, work). "
                        "Functions include hypothesis and future plans (ir a + inf), present subjunctive in main clauses (querer que, esperar que). "
                        "Discourse shows varied connectors (aunque, mientras, entonces, por eso). "
                        "No pluscuamperfecto subjunctive yet, limited register shifts.\n\n"
                        "B2 → obligatory pluscuamperfecto de indicativo AND consistent imperfect subjunctive in typical triggers (emoción, duda, concesión). "
                        "Lexicon includes abstract vocabulary (opinions, arguments, social issues). "
                        "Functions include hypothesis, concession, nuanced argumentation, and production of common idioms/proverbs. "
                        "Discourse shows rich markers (sin embargo, por lo tanto, además) and complex sentence linking. "
                        "Rare literary tenses not required, register still neutral.\n\n"
                        "C1 → presence of at least one rare tense (pretérito anterior, futuro perfecto, condicional perfecto, pluscuamperfecto de subjuntivo) used correctly. "
                        "Lexicon includes cultured, idiomatic phrasing and less common idioms/collocations. "
                        "Functions include register shifts (formal/informal), idiomatic expressions beyond common proverbs, nuanced argumentation. "
                        "Discourse shows cohesive, sophisticated connectors and fluid paragraph-level cohesion. "
                        "Respond ONLY with a JSON object of the form: "
                        "{ \"cefr_level\": \"A1|A2|B1|B2|C1\", \"reasoning\": \"justification\" } "
                    )
                },

                {"role": "user","content": "Me llamo Ana. Tengo 25 años. Vivo en Madrid."},
                {"role": "assistant","content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Only present tense, survival lexicon (introductions, age, residence). No modal or idiomatic expansions.\" }"},

                {"role": "user","content": "Tengo hambre y quiero comer una pizza."},
                {"role": "assistant","content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Idiomatic tener-phrase (hambre) and querer + inf show functional expansion beyond A1.\" }"},

                {"role": "user","content": "Ayer fui al cine con mis amigos y me gustó mucho."},
                {"role": "assistant","content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"First use of pretérito indefinido with basic connector y.\" }"},

                {"role": "user","content": "Cuando era pequeño, mi abuela me contaba cuentos antes de dormir."},
                {"role": "assistant","content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Correct contrast between imperfecto (era, contaba) and narrative context. Cohesive connector cuando.\" }"},

                {"role": "user","content": "Espero que vengas mañana a mi casa."},
                {"role": "assistant","content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Present subjunctive (vengas) triggered by esperar que, typical of B1 functional expansion.\" }"},

                {"role": "user","content": "Si hubiera estudiado más, habría aprobado el examen."},
                {"role": "assistant","content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Use of pluscuamperfecto subjunctive (hubiera estudiado) and condicional perfecto (habría aprobado) in hypothesis.\" }"},

                {"role": "user","content": "Aunque estaba cansado, seguí trabajando porque quería terminar el proyecto."},
                {"role": "assistant","content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Connector aunque with imperfecto, nuanced concession and causal discourse markers (porque).\" }"},

                {"role": "user","content": "De tal palo, tal astilla."},
                {"role": "assistant","content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Common proverb used appropriately; demonstrates idiomatic competence without rare tense or advanced register.\" }"},

                {"role": "user","content": "Apenas hube cerrado la puerta, sonó el teléfono."},
                {"role": "assistant","content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Rare tense pretérito anterior (hube cerrado) used correctly in literary register.\" }"},

                {"role": "user","content": "Si hubiera sabido la verdad, no habría dicho nada, pero al fin y al cabo todos cometemos errores."},
                {"role": "assistant","content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Pluscuamperfecto subjunctive with condicional perfecto, idiomatic connector 'al fin y al cabo' shows cultured phrasing and cohesive discourse.\" }"},

                {"role": "user","content": "No hay mal que por bien no venga; a la postre, fue una decisión sensata."},
                {"role": "assistant","content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Less common idiom plus cultured connector 'a la postre' shows advanced register and cohesive discourse.\" }"},

                # --- Actual request ---
                {"role": "user", "content": spanish_sentence}
            ]
                response_format={ "type": "json_object" },
                temperature=0.0,
                top_p=1.0,
                stream=False,
                max_completion_tokens=500,
            )

            raw_output = response.choices[0].message.content.strip()
            data = json.loads(raw_output)

            cefr_level = data.get("cefr_level", "UNKNOWN").strip()
            reasoning = data.get("reasoning", "").strip()

            # --- Strict validation ---
            if cefr_level not in valid_levels:
                print(f"⚠️ Invalid CEFR level: {cefr_level} → forcing UNKNOWN")
                cefr_level = "UNKNOWN"

            print(f"✅ CEFR level: {cefr_level}")
            return cefr_level, reasoning

        except Exception as e:
            print(f"⚠️ Attempt {attempt} failed on: {spanish_sentence} → {e}")
            if attempt < max_retries:
                time.sleep(pause)
                continue
            return "UNKNOWN", ""

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
    