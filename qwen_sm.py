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

# --- CEFR Mapping ---
CEFR_MAP = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}

# --- USER PROMPTS ---
# try:
#     SAMPLE_SIZE = int(input("Enter sample size (e.g., 1000): ").strip())
# except ValueError:
#     SAMPLE_SIZE = 1000
#     print("⚠️ Invalid input, defaulting SAMPLE_SIZE to 1000.")

#empty_choice = input("Do you want to wipe all AI ratings before regrading? (yes/no): ").strip().lower()
#EMPTY_COLLECTION = empty_choice in ["yes", "y", "true", "1"]
EMPTY_COLLECTION = False

# print(f"✅ SAMPLE_SIZE set to {SAMPLE_SIZE}")
# print(f"✅ EMPTY_COLLECTION set to {EMPTY_COLLECTION}")

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
                        "Your task: assign a CEFR level followed by an in‑depth justification.\n\n"

                        "A1 → only present tense (ser/estar, tener for age/family/possession, basic verbs like vivir, trabajar, gustar). "
                        "No modals, no idiomatic tener (hambre, frío, sueño), no periphrasis. "
                        "Connectors: y (and), o (or). "
                        "No contrast (pero), cause (porque), or time (cuando). "
                        "Use of less common nouns does not signal A2.\n\n"

                        "A2 → first use of pretérito indefinido/perfecto OR expansions: obligation (tener que, deber), "
                        "ability (poder, saber+inf), desire (querer+inf), idiomatic tener (hambre, frío, sueño). "
                        "Connectors: pero (contrast), porque (cause), cuando (time). "
                        "Future plans with ir a+inf are allowed. "
                        "No systematic tense contrast, no subjunctive. "
                        "Examples: Quiero viajar mañana porque tengo tiempo. Sé tocar la guitarra. Voy a llegar tarde.\n\n"

                        "B1 → systematic contrast between indefinido vs imperfecto (imperfect indicative vs simple past). "
                        "Lexicon: narrative (childhood, travel, work). "
                        "Functions: hypothesis, future plans (ir a+inf). "
                        "Present subjunctive belongs here in desire/hope clauses (quiero que vengas, espero que no llueva), "
                        "necessity/advice clauses (es mejor que estudies, es importante que descanses), "
                        "relative clauses (busco un piso que sea tranquilo), "
                        "and possibility markers (tal vez llegue, quizás venga). "
                        "Simple past narratives with opinions. "
                        "No imperfect subjunctive (si pudiera, quisiera) or pluscuamperfecto subjunctive at this level. "
                        "Connectors: aunque, mientras, entonces, por eso. "
                        "May use everyday connectors and near‑future expressions (estar a punto de + inf). "
                        "Examples: Quiero que sepas que te apoyo. Tal vez llegue más tarde. Pensaba ir al cine, pero me quedé en casa.\n\n"

                        "B2 → requires pluscuamperfecto indicativo AND consistent use of imperfect subjunctive in typical triggers "
                        "(emoción, duda, concesión). "
                        "Lexicon: abstract (opinions, arguments, social issues). "
                        "Functions: hypothesis, concession, nuanced argumentation, idioms/proverbs. "
                        "Connectors: sin embargo, por lo tanto, además. "
                        "Complex sentence linking, register neutral. "
                        "Present subjunctive alone does not qualify for B2. "
                        "Examples: Si pudiera, lo haría. Dudaba que vinieras. Había pensado que era mejor esperar.\n\n"

                        "C1 → at least one rare tense (pretérito anterior, futuro perfecto, condicional perfecto, pluscuamperfecto subjuntivo) used correctly. "
                        "Lexicon: cultured phrasing, less common idioms/collocations. "
                        "Functions: register shifts, idiomatic expressions beyond common proverbs, nuanced argumentation. "
                        "Discourse: cohesive, sophisticated connectors, paragraph‑level cohesion. "
                        "Examples: Habrá terminado antes de que llegues. Ojalá hubiera sabido la verdad. Hube terminado el trabajo cuando llegaste.\n\n"

                        "IMPORTANT: Pretérito anterior (hube + participio) and futuro perfecto (habrá + participio) are rare tenses. "
                        "Any correct use of them must be classified as C1. "
                        "Do not misclassify A2 or B1 sentences as B2 simply because they contain connectors, modals, or present subjunctive triggers.\n\n"

                        "Respond ONLY with a JSON object:\n"
                        "{ \"cefr_level\": \"A1|A2|B1|B2|C1\", \"reasoning\": \"justification\" } "
                    )
                },

                # Few‑shot examples
                { "role": "user", "content": "Me llamo Luis y vivo en Valencia." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Simple present tense, basic lexicon (introductions, residence), no expansions, A1.\" }" },
                
                { "role": "user", "content": "Me gusta caliente o frío." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Uses 'me gusta' with two adjectives joined by 'y'. Present tense only, no modals, no past tense, no expansions. This is A1.\" }" },
                
                { "role": "user", "content": "Me gusta la mermelada y el queso azul." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Uses 'me gusta' with two nouns joined by 'y'. Present tense only, no modals, no past tense, no expansions. This is A1.\" }" },

                { "role": "user", "content": "La mesa es grande y la silla es pequeña." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Simple present tense with connector 'y'. No expansions, no past tense. A1.\" }" },

                { "role": "user", "content": "Hoy es domingo y estoy en casa." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Present tense only, connector 'y', no expansions. This is A1.\" }" },

                { "role": "user", "content": "El libro está en la mesa y la ventana está abierta." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Simple present tense with 'y'. No modals, no past tense. A1.\" }" },

                { "role": "user", "content": "¿Dónde está el baño?" },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Basic present tense question, no expansions. A1.\" }" },

                { "role": "user", "content": "Mi casa es pequeña y bonita." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Present tense description with 'y'. No expansions. A1.\" }" },

                { "role": "user", "content": "Voy al supermercado y compro frutas y verduras." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Present tense verbs ('voy', 'compro') with connector 'y'. No past tense, no modals, no idiomatic tener, no connectors beyond 'y'. This is A1.\" }" },
                
                { "role": "user", "content": "Voy a la escuela y estudio matemáticas." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A1\", \"reasoning\": \"Uses present tense verbs ('voy', 'estudio') with connector 'y'. 'Voy a la escuela' is movement to a place, not 'ir a + infinitive' future. No expansions beyond A1.\" }" },

                { "role": "user", "content": "Voy a estudiar matemáticas mañana." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'ir a + infinitive' ('voy a estudiar') to express a future plan. The time marker 'mañana' reinforces the expansion. This is A2.\" }" },

                { "role": "user", "content": "Vivo cerca del parque y camino todos los días." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Present tense only, connector 'y'. No modals or past tense. A2.\" }" },
                
                { "role": "user", "content": "Puedo cocinar pasta y preparar ensalada." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'poder + infinitive' to express ability. This is a functional expansion typical of A2.\" }" },

                { "role": "user", "content": "Tengo que estudiar para el examen y hacer mis deberes." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'tener que + infinitive' to express obligation. This is an A2 construction.\" }" },

                { "role": "user", "content": "Quiero viajar a México el año que viene." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Use of querer+infinitive for desire, functional expansion typical of A2.\" }" },

                { "role": "user", "content": "Ellos necesitan descansar después del trabajo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Modal/functional expansion (necesitar+infinitive), everyday lexicon, typical of A2.\" }" },
                
                {"role": "user", "content": "Sé tocar la guitarra un poco."}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses saber + infinitive to express ability. This is typical A2 functional language.\" }"},
                
                {"role": "user", "content": "Voy a empezar un curso de fotografía."}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'ir a + infinitive' for future plans. This is an A2 construction, not B2.\" }"},
                
                {"role": "user", "content": "¿Sabes conducir o prefieres ir en taxi?"}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses saber + infinitive for ability and simple preference. These are A2 features.\" }"},
                
                {"role": "user", "content": "Cuando llego, te llamo porque no tengo tiempo."}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Simple present with connectors 'cuando' and 'porque'. These are A2 sentence structures.\" }"},
                
                {"role": "user", "content": "Deberías descansar; estás muy cansado."}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses modal deber + infinitive for advice. This is A2 functional language.\" }"},

                { "role": "user", "content": "Puedo ayudarte si quieres." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'poder + infinitive' ('puedo ayudarte') with a conditional clause in present indicative ('si quieres'). This is a straightforward A2 construction, not B2.\" }" },

                { "role": "user", "content": "Si quieres, vamos al cine." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'si + present indicative' ('si quieres') with a simple present plan ('vamos'). This is a straightforward A2 conditional construction.\" }" },

                { "role": "user", "content": "Si tienes hambre, comemos ahora." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'si + present indicative' ('si tienes') with a simple present action ('comemos'). This is a basic A2 conditional structure.\" }" },

                { "role": "user", "content": "Si estudias, aprendes más rápido." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"Uses 'si + present indicative' ('si estudias') with a present result ('aprendes'). This is a simple A2 conditional sentence.\" }" },

                {"role": "user", "content": "Quiero que vengas a mi fiesta."}, 
                {"role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive after querer. This is a B1 feature, not B2.\" }"},
                
                {"role": "user", "content": "Espero que no llueva mañana."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive after esperar with future reference. This is typical B1 usage.\" }"},
                
                {"role": "user", "content": "El año pasado viajé a Perú y fue inolvidable."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Simple past narrative with opinion. This is B1 storytelling, not B2.\" }"},
                
                {"role": "user", "content": "Estoy a punto de salir; voy a llegar tarde."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses 'estar a punto de' for near future and consequence. This is B1 functional language.\" }"},
                
                { "role": "user", "content": "Busco un profesor que sea paciente y amable." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive in a relative clause ('que sea paciente'). This is a B1 feature.\" }" },
                
                {"role": "user", "content": "Aunque estaba cansado, fui al cine."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Connector 'aunque' with simple past. This is a B1 sentence, not B2.\" }"},

                { "role": "user", "content": "Espero que tengas tiempo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive ('tengas') in a desire clause ('Espero que'). This is a standard B1 trigger, not B2.\" }" },

                { "role": "user", "content": "¿Has comido ya?" },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present perfect ('has comido') in a simple everyday question. Present perfect is introduced at B1 and does not require B2 complexity.\" }" },

                { "role": "user", "content": "Es mejor que estudies más." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive ('estudies') in an opinion clause ('Es mejor que'). This is a typical B1 construction, not B2.\" }" },

                { "role": "user", "content": "Cuando era pequeño, jugaba en el patio con mis primos." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Imperfecto in narrative context with connector 'cuando', typical of B1.\" }" },

                { "role": "user", "content": "De niño, siempre leía cuentos antes de dormir." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Imperfect tense used for habitual past actions, typical of B1.\" }" },
                
                { "role": "user", "content": "Si tuviera más dinero, viajaría por el mundo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Uses imperfect subjunctive ('tuviera') in a conditional clause. This construction is introduced at B2.\" }" },

                { "role": "user", "content": "Aunque llueva, iremos al parque." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Uses concessive subjunctive ('aunque llueva'). Concessive clauses with subjunctive are typical of B2.\" }" },
                
                { "role": "user", "content": "Habría estudiado más, pero no tuve tiempo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Uses conditional perfect ('habría estudiado'), which is introduced at B2. No rare idiomatic register elevates it to C1.\" }" },

                { "role": "user", "content": "Aunque llueva, iremos al concierto." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Imperfect subjunctive trigger (concesión) plus future plan, typical of B2.\" }" },

                { "role": "user", "content": "Si hubieras estudiado más, habrías aprobado el examen." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Conditional exception with 'si + pluscuamperfecto subjunctivo' and 'condicional perfecto'. This is a B2 anchor.\" }" },

                { "role": "user", "content": "Me gustaría que me lo explicaras con detalle." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Subjunctive trigger (gustar+que), nuanced request, typical of B2.\" }" },
                
                { "role": "user", "content": "Cuando termines, avísame." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive ('termines') in a temporal clause with imperative ('avísame'). Present subjunctive in common triggers is introduced at B1, not B2.\" }" },

                { "role": "user", "content": "Cuando hayas terminado, avísame." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Uses compound subjunctive ('hayas terminado') with imperative. Compound subjunctive forms are introduced at B2.\" }" },

                { "role": "user", "content": "Ojalá hubiera tenido más tiempo para terminar el proyecto." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses pluscuamperfecto subjunctivo in a wish ('hubiera tenido'). Rare tense forces C1.\" }" },

                { "role": "user", "content": "Apenas hube terminado, salí corriendo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Rare pretérito anterior tense used correctly, literary register, typical of C1.\" }" },

                { "role": "user", "content": "Para entonces, se habrá resuelto el conflicto." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Futuro perfecto construction, advanced temporal nuance, typical of C1.\" }" },

                {"role": "user", "content": "Habrá comido pan."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Sentence uses futuro perfecto ('habrá comido') with ultra-basic lexicon. Rare tense forces C1 regardless of simplicity.\" }"},

                {"role": "user", "content": "¿Habrá terminado el examen?"},
                {"role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Sentence uses futuro perfecto in a question ('¿Habrá terminado el examen?'). Rare tense forces C1 even in interrogatives.\" }"},
                
                { "role": "user", "content": "Aunque llueva, vamos al parque." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"Uses present subjunctive ('llueva') in a concessive clause. Present subjunctive in common triggers is introduced at B1.\" }" },

                { "role": "user", "content": "Aunque fuera difícil, lo intentaría." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"Uses imperfect subjunctive ('fuera') with conditional ('intentaría'). Imperfect subjunctive with conditional is typical of B2.\" }" },

                {"role": "user", "content": "Debería haber estudiado más."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Sentence combines condicional perfecto ('debería haber estudiado') with modal deber. Rare tense forces C1 despite modal overlap.\" }"},

                {"role": "user", "content": "Cuando hube llegado, ya se habían ido."},
                {"role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Sentence uses pretérito anterior ('hube llegado') within a narrative connector ('cuando'). Rare tense forces C1 regardless of narrative framing.\" }"},

                { "role": "user", "content": "Por ende, la decisión fue irrevocable." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses the rare formal connector 'por ende'. Even though the verb 'fue' is simple past, the idiomatic register forces classification at C1.\" }" },

                { "role": "user", "content": "En aras de la justicia, aceptó el castigo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses the rare idiomatic expression 'en aras de'. Despite the simple past verb 'aceptó', the formal idiomatic framing elevates the sentence to C1.\" }" },
                
                { "role": "user", "content": "Ojalá hubiera tenido más tiempo." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses pluscuamperfecto subjunctivo ('hubiera tenido') in a wish construction. This rare tense elevates the sentence to C1.\" }" },

                { "role": "user", "content": "Cuando hayas terminado el proyecto, habré viajado a Madrid." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses futuro perfecto ('habré viajado') combined with a subordinate clause. Rare tense usage places this at C1.\" }" },

                { "role": "user", "content": "Por ende, la propuesta fue rechazada." },
                { "role": "assistant", "content": "{ \"cefr_level\": \"C1\", \"reasoning\": \"Uses the rare formal connector 'por ende'. Even though the verb 'fue' is simple past, the idiomatic register forces classification at C1.\" }" },

                    # --- Actual request ---
                    {"role": "user", "content": spanish_sentence}
                ],
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
    