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
                                "Your task: assign a CEFR level (A1–C1) to the Spanish sentence with an in-depth justification.\n\n"

                                "A1 → only present tense (ser/estar, tener for age/family/possession, basic verbs). "
                                "No modals, no idiomatic tener expressions, no periphrasis. "
                                "Connectors: y, o, and pero. "
                                "Porque and cuando are A2.\n\n"

                                "A2 → first coordinated clauses (y, pero), connectors porque/cuando, ir a + inf, "
                                "obligation (tener que, hay que, deber), ability (poder, saber + inf), "
                                "present perfect (he comido hoy), idiomatic tener (hambre, sueño, calor). "
                                "No subjunctive.\n\n"

                                "B1 → includes present subjunctive and present perfect subjunctive (haya + participio) in emotion, doubt, wish, volition, or relative clauses. "
                                "Conditional present alone (me gustaría + infinitivo) = B1 unless other B2 signals are present.\n\n"

                                "CRITICAL SUBJUNCTIVE RULE (overrides everything else):\n"
                                "- Present subjunctive = ALWAYS B1\n"
                                "- Present PERFECT subjunctive (haya / hayas / hayan + participio) = ALWAYS B1\n"
                                "- ONLY imperfect subjunctive (hablara / hubiese) or pluperfect subjunctive (hubiera + participio) can push a sentence to B2 or higher\n\n"

                                "B2 → requires imperfect or pluperfect subjunctive, or compound/advanced tenses (conditional perfect, futuro perfecto, temporal/subordinate clauses with subjunctive). "
                                "Conditional + imperfect subjunctive in polite requests (me gustaría que + V-ara/iese) = B2. "
                                "Other triggers: type-2 and type-3 conditionals, aunque/por mucho que + subj., ojalá + hubiera, futuro perfecto, condicional perfecto, concessive/argumentative discourse.\n\n"

                                "C1 → genuinely rare structures: pretérito anterior (hube + participio), "
                                "formal fixed expressions (sea como fuere, quiérase o no, a poco que, mal que le pese, "
                                "en aras de, habida cuenta de, a la postre, ni por asomo), sophisticated register shifts.\n\n"

                                "CRITICAL CORRECTIONS:\n"
                                "- Futuro perfecto (habrá + participio) = B2 (not C1)\n"
                                "- Condicional perfecto (habría + participio) = B2 (not C1)\n"
                                "- Type-3 conditionals (Si hubieras…, habría…) = B2 (not C1)\n"
                                "- Pluscuamperfecto indicativo (había + participio) = B1 (not B2)\n"
                                "- The ONLY tense that automatically triggers C1 is pretérito anterior (hube/hubiste… + participio)\n\n"

                                "Respond EXCLUSIVELY with valid JSON:\n"
                                "{ \"cefr_level\": \"A1|A2|B1|B2|C1\", "
                                "\"reasoning\": \"detailed justification in 1–2 sentences\", "
                                "\"grammar\": [\"grammatical categories only, e.g. present tense, imperfect subjunctive, conditional perfect, fixed expression. NOTHING in patentheses!\"] }"
                            )
                            },

                                            # Few‑shot examples
                                            {"role": "user", "content": "Me llamo Luis."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic self-introduction, present tense ser.\"}"},

                                            {"role": "user", "content": "¿Cómo te llamas?"},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic question with ser.\"}"},

                                            {"role": "user", "content": "Tengo 25 años."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Tener for age, numbers.\"}"},

                                            {"role": "user", "content": "La mesa es grande."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Ser + adjective description.\"}"},

                                            {"role": "user", "content": "Quiero un café, por favor."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Querer + noun, basic request.\"}"},

                                            {"role": "user", "content": "Vivo en una casa y tengo un perro."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Two clauses coordinated with y.\"}"},

                                            {"role": "user", "content": "Miro la televisión y descanso."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Classic A2 compound sentence with y.\"}"},

                                            {"role": "user", "content": "Hoy es lunes y voy al trabajo."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Coordination + time marker.\"}"},

                                            {"role": "user", "content": "Me gusta el fútbol y juego los sábados."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Gustar + activity + frequency.\"}"},

                                            {"role": "user", "content": "Voy al supermercado porque necesito leche."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Causal connector porque.\"}"},

                                            {"role": "user", "content": "Esta tarde he quedado con Ana."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect for near-future plans, very common A2.\"}"},

                                            {"role": "user", "content": "Puedo ayudarte si quieres."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Poder + infinitive, si + present.\"}"},

                                            {"role": "user", "content": "Tengo que estudiar para el examen."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Tener que + infinitive obligation.\"}"},
                                            
                                            {"role": "user", "content": "Me duele la garganta desde el viernes."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Physical sensation + desde + specific past point (duration up to present) = core B1 time marker.\"}"},

                                            { "role": "user", "content": "Es mejor que vengas temprano." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: evaluative clause with present subjunctive, common trigger.\" }" },

                                            { "role": "user", "content": "Es necesario que estudies más." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: subjunctive in opinion clause, everyday register.\" }" },

                                            { "role": "user", "content": "Cuando llegué, vi a mis amigos." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: temporal clause with indicative, narrative sequencing.\" }" },

                                            { "role": "user", "content": "Cuando era niño, jugaba en el parque." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: imperfect narrative with temporal connector cuando.\" }" },

                                            { "role": "user", "content": "Hoy he visto a mis abuelos." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"A2: present perfect for recent everyday event.\" }" },

                                            { "role": "user", "content": "Ya he terminado los deberes." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"A2\", \"reasoning\": \"A2: present perfect in everyday context, simple completion.\" }" },

                                            { "role": "user", "content": "Me alegro de que hayas venido." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: present perfect subjunctive in emotion clause.\" }" },

                                            { "role": "user", "content": "Espero que hayas tenido buen viaje." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: present perfect subjunctive in wish clause.\" }" },

                                            { "role": "user", "content": "Me gustaría que me ayudaras mañana." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional + imperfect subjunctive for polite request.\" }" },

                                            { "role": "user", "content": "Preferiría que me lo explicaras con calma." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional preference + imperfect subjunctive.\" }" },

                                            {"role": "system", "content": "CRITICAL 2025 DELE RULE: ANY sentence with present subjunctive in common triggers (querer que, ojalá, temo que, es importante que, me da igual que, busco que, etc.) OR present perfect (he comido) OR imperfect vs preterite contrast OR hace + time + que OR childhood imperfect → is B1 unless it contains conditional sentences, pluperfect subjunctive, future perfect, por mucho que, aunque + subjunctive, or archaic forms."},

                                            {"role": "user", "content": "Fue entonces cuando entendí lo que pasaba."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Classic B1 narrative cleft with preterite (DELE B1 official).\"}"},

                                            {"role": "user", "content": "Estoy a punto de salir; voy a llegar tarde."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Estar a punto de + infinitive = B1 imminent future periphrasis (Plan Curricular B1).\"}"},

                                            {"role": "user", "content": "Tal vez llegue más tarde; no estoy seguro."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Tal vez + present subjunctive and no estoy seguro de + inf = B1 doubt/possibility expressions.\"}"},

                                            {"role": "user", "content": "Me temo que no lleguemos a tiempo."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Me temo que + present subjunctive = B1 emotion/doubt verb (DELE B1 official).\"}"},

                                            {"role": "user", "content": "He visitado a mis abuelos este fin de semana."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect for recent experience (this weekend) = B1 experiential use.\"}"},

                                            {"role": "user", "content": "Ayer fui al cine con mis amigos."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Indefinido with ayer = B1 simple past narrative (Plan Curricular B1).\"}"},

                                            {"role": "user", "content": "Me duele la cabeza, pero sigo trabajando."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Physical complaint + pero contrast in present = B1 personal narrative (DELE B1).\"}"},

                                            {"role": "user", "content": "Ojalá nieve mañana."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Ojalá + present subjunctive = core B1.\"}"},

                                            {"role": "user", "content": "Quiero que vengas a cenar."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Querer que + present subjunctive = first systematic subjunctive, B1.\"}"},

                                            {"role": "user", "content": "Me temo que perdemos el avión."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Temo que + subjunctive = B1 emotion verb.\"}"},

                                            {"role": "user", "content": "Busco un piso que tenga ascensor."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative subjunctive = B1.\"}"},

                                            {"role": "user", "content": "He leído cuatro libros este verano."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect for recent past = B1.\"}"},

                                            {"role": "user", "content": "Cuando era pequeño vivía en un pueblo."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect for childhood = B1.\"}"},

                                            {"role": "user", "content": "Pensaba ir al cine, pero me quedé en casa."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Indefinido/imperfecto contrast + pero = classic B1 narrative.\"}"},

                                            {"role": "user", "content": "Hace cinco años que estudio español."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Hace + time + que + present = B1 duration.\"}"},
                                            
                                            { "role": "user", "content": "Es mejor que vengas temprano." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: evaluative clause with present subjunctive, common trigger.\" }" },

                                            { "role": "user", "content": "Es importante que estudies para el examen." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: opinion clause with present subjunctive, everyday register.\" }" },

                                            { "role": "user", "content": "Me parece mal que no vengas." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: evaluative clause with present subjunctive, simple opinion.\" }" },
                                            
                                            { "role": "user", "content": "El verano pasado fui a la playa y fue fantástico." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: indefinido narrative with evaluative adjective, simple past experience.\" }" },

                                            { "role": "user", "content": "Ayer cené con amigos y estuvo genial." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: simple past (indefinido) with evaluative adjective, everyday narrative.\" }" },

                                            { "role": "user", "content": "Hace dos años viajé a Italia y fue increíble." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: past narrative with evaluation, no subjunctive or conditional.\" }" },

                                            { "role": "user", "content": "Quiero un profesor que sea paciente." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: relative clause with present subjunctive, common everyday trigger.\" }" },

                                            { "role": "user", "content": "Busco un piso que tenga balcón." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: present subjunctive in relative clause, indefinite antecedent.\" }" },

                                            { "role": "user", "content": "Necesito un coche que funcione bien." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: relative clause with present subjunctive, everyday context.\" }" },
                                            
                                            { "role": "user", "content": "Me encanta que participes en clase." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: everyday attitude clause with present subjunctive, positive reaction.\" }" },

                                            { "role": "user", "content": "Me sorprende que llegues tan temprano." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: attitude clause with present subjunctive, everyday surprise expression.\" }" },

                                            { "role": "user", "content": "Me fastidia que olvides las llaves." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B1\", \"reasoning\": \"B1: attitude clause with present subjunctive, everyday annoyance expression.\" }" },

                                            { "role": "user", "content": "Me gustaría que me acompañaras al banco mañana." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional + imperfect subjunctive, polite evaluative request.\" }" },

                                            { "role": "user", "content": "Preferiría que me lo entregaras por escrito." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional preference + imperfect subjunctive, evaluative nuance.\" }" },

                                            { "role": "user", "content": "Es posible que hayas olvidado el documento." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: evaluative clause with present perfect subjunctive, compound tense.\" }" },

                                            { "role": "user", "content": "Buscaba un piso que fuera tranquilo." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: imperfect subjunctive in relative clause, past context.\" }" },

                                            { "role": "user", "content": "Quería un profesor que ayudara a todos." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: imperfect subjunctive in relative clause, past desire.\" }" },

                                            { "role": "user", "content": "Habría preferido un coche que hubiera sido más rápido." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: pluperfect subjunctive in relative clause, conditional nuance.\" }" },

                                            { "role": "user", "content": "Preferiría que me lo contaras mañana." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional preference + imperfect subjunctive, evaluative nuance.\" }" },

                                            { "role": "user", "content": "Es posible que haya perdido el móvil." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: evaluative clause with present perfect subjunctive, expressing possibility.\" }" },

                                            { "role": "user", "content": "Preferiría que me lo explicaras con calma." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional preference + imperfect subjunctive.\" }" },

                                            { "role": "user", "content": "Querría que me acompañaras al médico." },
                                            { "role": "assistant", "content": "{ \"cefr_level\": \"B2\", \"reasoning\": \"B2: conditional desire + imperfect subjunctive, polite nuance.\" }" },
                                            
                                            {"role": "user", "content": "Si tuviera dinero, viajaría."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Type-2 hypothetical (imperfect subjunctive + conditional).\"}"},

                                            {"role": "user", "content": "Si hubieras estudiado, habrías aprobado."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Type-3 unreal past conditional.\"}"},

                                            {"role": "user", "content": "Aunque llueva, iremos al parque."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Aunque + present subjunctive (hypothetical concession).\"}"},

                                            {"role": "user", "content": "Cuando termines, avísame."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Cuando + present subjunctive for future action.\"}"},

                                            {"role": "user", "content": "Para que no te pierdas, te doy un mapa."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Para que + subjunctive (purpose).\"}"},

                                            {"role": "user", "content": "Habrá terminado antes de las cinco."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Future perfect.\"}"},

                                            {"role": "user", "content": "Habría venido si me hubieras avisado."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Conditional perfect.\"}"},

                                            {"role": "user", "content": "De no ser por ti, no lo habríamos conseguido."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"De no ser por + conditional perfect.\"}"},

                                            {"role": "user", "content": "Por mucho que corra, no llegaré a tiempo."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Por mucho que + subjunctive concession.\"}"},

                                            {"role": "user", "content": "Ojalá hubiera llovido ayer."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Ojalá + pluperfect subjunctive.\"}"},
                                            
                                            {"role": "user", "content": "En caso de que surjan complicaciones, llámame inmediatamente."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"En caso de que + present subjunctive = B2 conditional connector (Plan Curricular B2).\"}"},

                                            {"role": "user", "content": "En caso de que necesiten ayuda extra, estaré en la oficina hasta tarde."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"En caso de que + present subjunctive for future contingency = B2.\"}"},

                                            {"role": "user", "content": "En caso de que aprueben la nueva ley, tendremos que cambiar el plan."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"En caso de que + present subjunctive = standard B2 structure.\"}"},

                                            {"role": "user", "content": "En caso de que llueva mañana, cancelaremos el picnic."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"En caso de que + present subjunctive = B2 conditional clause.\"}"},

                                            {"role": "user", "content": "Es normal que esté cansado después del viaje."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Es normal que + subjunctive.\"}"},

                                            {"role": "user", "content": "Apenas hube terminado, sonó el teléfono."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Pretérico anterior (very rare literary tense).\"}"},

                                            {"role": "user", "content": "Sea como fuere, debemos seguir adelante."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal concessive expression with subjunctive.\"}"},

                                            {"role": "user", "content": "Por más que lo intenté, no lo conseguí."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Por más que + indicative (formal concession).\"}"},

                                            {"role": "user", "content": "Así las cosas, poco podemos hacer."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal discourse marker.\"}"},

                                            {"role": "user", "content": "Con todo, aceptaron la propuesta."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal adversative connector.\"}"},

                                            {"role": "user", "content": "En aras de la transparencia, publicaremos los datos."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression.\"}"},

                                            {"role": "user", "content": "Quiérase o no, tendremos que adaptarnos."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Impersonal formal subjunctive construction.\"}"},

                                            {"role": "user", "content": "A poco que te esfuerces, lo conseguirás."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"A poco que + subjunctive (nuanced concession).\"}"},

                                            {"role": "user", "content": "Habida cuenta de las circunstancias, actuaremos con cautela."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal fixed expression.\"}"},

                                            {"role": "user", "content": "Mal que le pese, deberá disculparse."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal concessive with subjunctive.\"}"},

                                            {"role": "user", "content": "De haberlo sabido, habría actuado distinto."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Inverted pluperfect subjunctive construction (formal).\"}"},

                                            {"role": "user", "content": "A la postre, todo salió bien."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Literary temporal expression.\"}"},

                                            {"role": "user", "content": "Ni por asomo se me ocurrió que pudiera pasar."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Strong idiomatic negation.\"}"},
                                            
                                            {"role": "user", "content": "En caso de que hubiere inconvenientes de última hora, se aplazará la ceremonia."},
                                            {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Future subjunctive (hubiere) after 'en caso de que' + formal passive future = automatic C1 (only surviving context for future subjunctive in modern Spanish).\"}"},
                                            
                                            
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
    