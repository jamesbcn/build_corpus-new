import json
import re

# --- 1. PASTE THE CLEAN SYSTEM PROMPT CONTENT HERE (USE THE PROVIDED TEXT) ---
# Paste the FULL_SYSTEM_PROMPT_CONTENT text here
FULL_SYSTEM_PROMPT_CONTENT = """
Your task: assign a CEFR level (A1–C1) to the Spanish sentence. Respond ONLY with valid JSON.

OFFICIAL 2025 RULES (Instituto Cervantes / DELE / SIELE – no exceptions):

A1 → only present indicative (ser, estar, tener for age/possession/family, llamarse, vivir, trabajar, basic regular verbs, gustar, querer + noun).
Connectors: only y, o, pero (very rare).
No modals, no periphrasis, no tener idioms, no past tenses.

A2 → coordinated clauses, connectors porque / cuando / si (real condition), ir a + inf, poder / saber / querer / deber + inf, tener que / hay que.
Present perfect indicative with hoy / esta mañana / esta semana / ya / nunca / jamás.
Idiomatic tener (hambre, sed, sueño, calor, frío, prisa, razón).
Preterite indefinite (indefinido) introduced here.
NO subjunctive of any kind.

B1 → first systematic subjunctive appearance.
Present subjunctive → ALWAYS B1
Present perfect subjunctive (haya / hayas / hayan + participio) → ALWAYS B1
Also: imperfect vs preterite contrast, pluperfect indicative (había + participio), hace + time + que, experiential present perfect (este año he viajado…), me gustaría + infinitive, estar a punto de, tal vez + subj.

CRITICAL SUBJUNCTIVE RULE (overrides everything):
Any present subjunctive OR present perfect subjunctive = B1
ONLY imperfect subjunctive (-ra/-se) or pluperfect subjunctive pushes to B2+

B2 → REQUIRES at least one of:
• Imperfect subjunctive or pluperfect subjunctive (me gustaría que + -ra/-se, type-2/3 conditionals, aunque / por mucho que / en caso de que + subj., etc.)
• Future perfect, conditional perfect
• Concessive/argumentative connectors with subjunctive

C1 → genuinely rare / formal / literary only:
• Pretérito anterior (hube + participio)
• Future subjunctive (hubiere, fuere, dijere…)
• Fixed formal expressions: sea como fuere, quiérase o no, mal que le pese, habida cuenta de, en aras de, a la postre, ni por asomo, dado el caso, visto bueno, etc.
• Sophisticated register shifts and low-frequency formal vocabulary

CRITICAL CLARIFICATIONS:
• me gustaría + infinitive = B1  |  me gustaría que + imperfect subjunctive = B2
• Present perfect with hoy/ya = A2  |  with este año/verano = B1
• Pluperfect indicative (había + participio) = B1
• Future perfect & conditional perfect = B2
• Pretérito anterior = the ONLY automatic C1 tense

Respond EXCLUSIVELY with valid JSON:
{ "cefr_level": "A1|A2|B1|B2|C1",
"reasoning": "Clear, concise justification in 1–2 sentences using the rules above.",
"grammar": ["Present Indicative", "Present Perfect Indicative", "Present Subjunctive", "Imperfect Subjunctive", "Conditional Perfect", "Fixed Formal Expression", "..."]
}
Grammar tags in English only, no parentheses, no Spanish examples inside the array.
"""


# --- 2. PASTE THE ENTIRE USER/ASSISTANT CHAT BLOCK HERE (YOUR 400+ EXAMPLES) ---
# Paste the FEWSHOTS_BLOCK text here
FEWSHOTS_BLOCK = """
{"role": "user", "content": "Me llamo Luis."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic self-introduction using the reflexive verb llamarse.\", \"grammar\": [\"Present Indicative\"]}"},

                                                {"role": "user", "content": "¿Cómo te llamas?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic identity question.\", \"grammar\": [\"Present Indicative\", \"Question Formation\"]}"},

                                                {"role": "user", "content": "Leo un libro y bebo té."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Two simple present-tense actions joined only by y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},

                                                {"role": "user", "content": "Tengo 25 años."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Classic use of tener to express age.\", \"grammar\": [\"Present Indicative\", \"Tener for Age\"]}"},

                                                {"role": "user", "content": "La mesa es grande."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Ser + adjective for permanent characteristic.\", \"grammar\": [\"Present Indicative\", \"Ser + Adjective\"]}"},

                                                {"role": "user", "content": "Quiero un café, por favor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Querer + noun for basic request.\", \"grammar\": [\"Present Indicative\"]}"},

                                                {"role": "user", "content": "Vivo en una casa y tengo un perro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Same-subject coordination using only y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},

                                                {"role": "user", "content": "Miro la televisión y descanso."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Classic A1 compound sentence with y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},

                                                {"role": "user", "content": "Hoy es lunes y voy al trabajo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Coordination + specific time marker.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},

                                                {"role": "user", "content": "Me gusta el fútbol y juego los sábados."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Gustar + frequency expression.\", \"grammar\": [\"Gustar\", \"Frequency Expression\"]}"},

                                                {"role": "user", "content": "Voy al supermercado porque necesito leche."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"First causal connector porque.\", \"grammar\": [\"Present Indicative\", \"Causal Connector porque\"]}"},

                                                {"role": "user", "content": "Esta tarde he quedado con Ana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect for near-future/recent plans with specific time marker.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "El billete costará unos 50 euros, creo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple future for price estimation.\", \"grammar\": [\"Simple Future\"]}"},

                                                {"role": "user", "content": "Puedo ayudarte si quieres."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Modal poder + infinitive and real conditional.\", \"grammar\": [\"Poder + Infinitive\", \"Real Conditional si + present\"]}"},

                                                {"role": "user", "content": "Tengo que estudiar para el examen."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Obligation with tener que + infinitive.\", \"grammar\": [\"Tener que + Infinitive\"]}"},

                                                {"role": "user", "content": "Mi móvil cayó al agua ayer."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple preterite indefinite with specific time marker.\", \"grammar\": [\"Preterite Indefinite\"]}"},

                                                {"role": "user", "content": "¿Cuántos cafés tomas al día?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Quantity question + frequency expression.\", \"grammar\": [\"Frequency Expression\", \"Question Formation\"]}"},

                                                {"role": "user", "content": "Hoy he visto a mis abuelos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect with 'hoy' = A2 immediate recent past (DELE A2 official).\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Hemos visto esa película dos veces."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Experiential present perfect with frequency = B1 life experience (DELE B1 official).\", \"grammar\": [\"Present Perfect Indicative\", \"Frequency Expression\"]}"},

                                                {"role": "user", "content": "Hoy he desayunado muy temprano."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect + hoy = immediate recent past, core A2.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Esta mañana he ido al mercado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect + esta mañana/semana = A2 recent past with specific time frame.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Ya he terminado los deberes."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect + ya = immediate completion, classic A2.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Esta semana he estado muy ocupado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect + esta semana = recent past, still A2.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Hoy he comido paella por primera vez."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + hoy + life experience ('por primera vez') = B1 experiential use.\", \"grammar\": [\"Present Perfect Indicative\", \"Life Experience\"]}"},

                                                {"role": "user", "content": "He estado en España tres veces."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + frequency in life ('tres veces') = B1 life experience.\", \"grammar\": [\"Present Perfect Indicative\", \"Frequency Expression\"]}"},

                                                {"role": "user", "content": "Este año he leído cinco libros de García Márquez."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + broader time frame + quantity = B1 experiential.\", \"grammar\": [\"Present Perfect Indicative\", \"Life Experience\"]}"},

                                                {"role": "user", "content": "Nunca he probado el sushi."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + nunca = life experience up to now, B1.\", \"grammar\": [\"Present Perfect Indicative\", \"Life Experience\"]}"},

                                                {"role": "user", "content": "En mi vida he visto una tormenta tan fuerte."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + 'en mi vida' = strong life experience marker, B1.\", \"grammar\": [\"Present Perfect Indicative\", \"Life Experience\"]}"},

                                                {"role": "user", "content": "Este verano he viajado a Italia con mis amigos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + este verano (finished period) + experience narrative = B1.\", \"grammar\": [\"Present Perfect Indicative\", \"Life Experience\"]}"},

                                                {"role": "user", "content": "Todavía no he recibido tu correo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect + todavía no = resultative/experiential up to now, B1.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "¿Cuántas veces has estado en Madrid?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Question about life experience + frequency = official DELE B1 oral task.\", \"grammar\": [\"Present Perfect Indicative\", \"Question Formation\"]}"},
                                            
                                                {"role": "user", "content": "Me duele la garganta desde el viernes."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Physical sensation + desde + specific past point.\", \"grammar\": [\"Desde hace / Desde + point\"]}"},

                                                {"role": "user", "content": "Es mejor que vengas temprano."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Evaluative expression requiring present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Es necesario que estudies más."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Evaluative/necessity expression + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Cuando llegué, vi a mis amigos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Temporal clause with preterite for narrative sequence.\", \"grammar\": [\"Preterite Indefinite\", \"Imperfect vs Preterite Contrast\"]}"},

                                                {"role": "user", "content": "Cuando era niño, jugaba en el parque."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect for habitual past / description in childhood.\", \"grammar\": [\"Imperfect Indicative\"]}"},

                                                {"role": "user", "content": "Ya he terminado los deberes."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect with ya for recent completion.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Me alegro de que hayas venido."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Espero que hayas tenido buen viaje."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Wish verb + present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Me gustaría que me ayudaras mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Polite request using conditional + imperfect subjunctive.\", \"grammar\": [\"Imperfect Subjunctive\", \"Me gustaría / Preferiría / Ojalá + Imperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "Preferiría que me lo explicaras con calma."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Polite preference with conditional + imperfect subjunctive.\", \"grammar\": [\"Imperfect Subjunctive\", \"Me gustaría / Preferiría / Ojalá + Imperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "Siempre que salgo sin paraguas, llueve."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Siempre que + present indicative for habitual correlation.\", \"grammar\": [\"Temporal Clause with Subjunctive\"]}"},

                                                {"role": "user", "content": "Fue entonces cuando entendí lo que pasaba."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Narrative cleft structure with preterite.\", \"grammar\": [\"Preterite Indefinite\"]}"},

                                                {"role": "user", "content": "Estoy a punto de salir; voy a llegar tarde."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imminent future periphrasis.\", \"grammar\": [\"Estar + Gerund\", \"Ir a + Infinitive\"]}"},

                                                {"role": "user", "content": "Tal vez llegue más tarde; no estoy seguro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Doubt expressions with present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Tal vez + Subjunctive\"]}"},

                                                {"role": "user", "content": "Me temo que no lleguemos a tiempo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion/doubt verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "He visitado a mis abuelos este fin de semana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Experiential present perfect with broader time frame.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Ayer fui al cine con mis amigos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Simple past narrative with preterite.\", \"grammar\": [\"Preterite Indefinite\"]}"},

                                                {"role": "user", "content": "Me duele la cabeza, pero sigo trabajando."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Contrast with pero in personal narrative.\", \"grammar\": [\"Connector pero\"]}"},

                                                {"role": "user", "content": "Ojalá nieve mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Wish expression with present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Ojalá + Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Quiero que vengas a cenar."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Volition verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Me temo que perdemos el avión."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Busco un piso que tenga ascensor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative clause with present subjunctive (indefinite antecedent).\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "He leído cuatro libros este verano."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Experiential present perfect with broader time frame.\", \"grammar\": [\"Present Perfect Indicative\"]}"},

                                                {"role": "user", "content": "Cuando era pequeño vivía en un pueblo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect for past description/habit.\", \"grammar\": [\"Imperfect Indicative\"]}"},

                                                {"role": "user", "content": "Pensaba ir al cine, pero me quedé en casa."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Classic imperfect vs preterite contrast.\", \"grammar\": [\"Imperfect vs Preterite Contrast\"]}"},

                                                {"role": "user", "content": "Hace cinco años que estudio español."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Duration up to present with hace + time + que.\", \"grammar\": [\"Hace + time + que + present\"]}"},

                                                {"role": "user", "content": "Es importante que estudies para el examen."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Evaluative expression + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Me parece mal que no vengas."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Evaluative expression + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Quiero un profesor que sea paciente."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative subjunctive with indefinite antecedent.\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "Busco un piso que tenga balcón."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative subjunctive seeking non-specific item.\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "Necesito un coche que funcione bien."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative subjunctive with indefinite antecedent.\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "Me encanta que participes en clase."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Me sorprende que llegues tan temprano."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Me fastidia que olvides las llaves."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},

                                                {"role": "user", "content": "Es posible que hayas olvidado el documento."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect subjunctive after evaluative expression.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Buscaba un piso que fuera tranquilo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Imperfect subjunctive in past-context relative clause.\", \"grammar\": [\"Imperfect Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "Quería un profesor que ayudara a todos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Imperfect subjunctive in past desire relative clause.\", \"grammar\": [\"Imperfect Subjunctive\", \"Relative Subjunctive\"]}"},

                                                {"role": "user", "content": "Habría preferido un coche que hubiera sido más rápido."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Pluperfect subjunctive in hypothetical relative clause.\", \"grammar\": [\"Pluperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "Si tuviera dinero, viajaría."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Type-2 hypothetical conditional.\", \"grammar\": [\"Imperfect Subjunctive\", \"Type-2 Conditional\"]}"},

                                                {"role": "user", "content": "Si hubieras estudiado, habrías aprobado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Type-3 unreal past conditional.\", \"grammar\": [\"Pluperfect Subjunctive\", \"Type-3 Conditional\"]}"},

                                                {"role": "user", "content": "Aunque llueva, iremos al parque."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Concessive aunque + present subjunctive (hypothetical).\", \"grammar\": [\"Aunque + Subjunctive\", \"Concessive Connector\"]}"},

                                                {"role": "user", "content": "Cuando termines, avísame."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Future-referring temporal clause with present subjunctive.\", \"grammar\": [\"Cuando + Subjunctive (future reference)\"]}"},

                                                {"role": "user", "content": "Para que no te pierdas, te doy un mapa."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Purpose clause with para que + subjunctive.\", \"grammar\": [\"Para que + Subjunctive\", \"Purpose Clause\"]}"},

                                                {"role": "user", "content": "Habrá terminado antes de las cinco."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Future perfect tense.\", \"grammar\": [\"Future Perfect\"]}"},

                                                {"role": "user", "content": "Habría venido si me hubieras avisado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Conditional perfect in mixed conditional.\", \"grammar\": [\"Conditional Perfect\"]}"},

                                                {"role": "user", "content": "De no ser por ti, no lo habríamos conseguido."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Inverted conditional perfect structure.\", \"grammar\": [\"Conditional Perfect\"]}"},

                                                {"role": "user", "content": "Por mucho que corra, no llegaré a tiempo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Strong concessive with por mucho que + subjunctive.\", \"grammar\": [\"Por mucho/más que + Subjunctive\", \"Concessive Connector\"]}"},

                                                {"role": "user", "content": "Ojalá hubiera llovido ayer."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Wish about the past with pluperfect subjunctive.\", \"grammar\": [\"Pluperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "En caso de que surjan complicaciones, llámame inmediatamente."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Contingency clause with en caso de que + present subjunctive.\", \"grammar\": [\"En caso de que + Subjunctive\"]}"},

                                                {"role": "user", "content": "Mal que les pese a los críticos, la película fue un éxito rotundo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal concessive expression, 'Mal que le pese,' which is high-level administrative register.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Habida cuenta de lo anterior, la junta directiva tomó una decisión ejecutiva."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression ('Habida cuenta de') used as a sophisticated discourse marker.\", \"grammar\": [\"Fixed Formal Expression\", \"Discourse Marker\"]}"},

                                                {"role": "user", "content": "El libro, quiérase o no, redefinió los paradigmas del género."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Impersonal, fixed concessive phrase ('quiérase o no') requiring the present subjunctive, high formal register.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Ni por asomo se me ocurrió que hubiese habido una traición."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Strong idiomatic negation ('Ni por asomo') combined with pluperfect subjunctive (hubiese habido), indicating high proficiency.\", \"grammar\": [\"Fixed Idiomatic Expression\", \"Pluperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "Se actuará con rigor, sea cual fuere el costo final."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed, formal expression ('sea cual fuere') requiring the present subjunctive, typical of administrative language.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Es normal que esté cansado después del viaje."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Evaluative adjective + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},

                                                {"role": "user", "content": "Mal que les pese a los críticos, la película fue un éxito rotundo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal concessive expression, 'Mal que le pese,' which is high-level administrative register.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Habida cuenta de lo anterior, la junta directiva tomó una decisión ejecutiva."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression ('Habida cuenta de') used as a sophisticated discourse marker.\", \"grammar\": [\"Fixed Formal Expression\", \"Discourse Marker\"]}"},

                                                {"role": "user", "content": "El libro, quiérase o no, redefinió los paradigmas del género."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Impersonal, fixed concessive phrase ('quiérase o no') requiring the present subjunctive, high formal register.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Ni por asomo se me ocurrió que hubiese habido una traición."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Strong idiomatic negation ('Ni por asomo') combined with pluperfect subjunctive (hubiese habido), indicating high proficiency.\", \"grammar\": [\"Fixed Idiomatic Expression\", \"Pluperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "Se actuará con rigor, sea cual fuere el costo final."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed, formal expression ('sea cual fuere') requiring the present subjunctive, typical of administrative language.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},

                                                {"role": "user", "content": "Apenas hube terminado, sonó el teléfono."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Pretérico anterior (extremely rare literary tense).\", \"grammar\": [\"Preterite Anterior\"]}"},

                                                {"role": "user", "content": "Sea como fuere, debemos seguir adelante."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal concessive fixed expression.\", \"grammar\": [\"Fixed Formal Expression\"]}"},

                                                {"role": "user", "content": "Por mucho que corro, siempre llego tarde."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Concessive por mucho que + indicative (real concession).\", \"grammar\": [\"Concessive Connector\"]}"},

                                                {"role": "user", "content": "En aras de la transparencia, publicaremos los datos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal fixed expression.\", \"grammar\": [\"Fixed Formal Expression\"]}"},

                                                {"role": "user", "content": "Quiérase o no, tendremos que adaptarnos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Impersonal formal construction with present subjunctive.\", \"grammar\": [\"Fixed Formal Expression\"]}"},

                                                {"role": "user", "content": "Mal que le pese, deberá disculparse."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal concessive expression.\", \"grammar\": [\"Fixed Formal Expression\"]}"},

                                                {"role": "user", "content": "De haberlo sabido, habría actuado distinto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Inverted formal conditional construction.\", \"grammar\": [\"Pluperfect Subjunctive\"]}"},

                                                {"role": "user", "content": "En caso de que hubiere inconvenientes de última hora, se aplazará la ceremonia."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Future subjunctive (only surviving modern use).\", \"grammar\": [\"Future Subjunctive\"]}"},
                                                
                                                {"role": "user", "content": "Tengo un coche, pero es viejo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple possession and description linked by the connector pero.\", \"grammar\": [\"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "El perro es grande y la casa es pequeña."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple descriptions using ser, linked by the connector y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "El libro está cerrado o está abierto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple description of state using estar, linked by the connector o.\", \"grammar\": [\"Present Indicative\", \"Connector o\"]}"},
                                                {"role": "user", "content": "Vivo en Barcelona y mi oficina está en el centro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple actions and locations using vivir and estar, linked by y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Quiero comprar pan, por favor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic request using querer + infinitive.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Mi hermana tiene un trabajo nuevo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple possession using tener.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Me gusta el color azul."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic expression of taste with gustar.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Ella es médica y trabaja mucho."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple identity and habitual action using ser and trabajar, linked by y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Necesito agua o zumo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple necessity using necesitar and the connector o.\", \"grammar\": [\"Present Indicative\", \"Connector o\"]}"},
                                                {"role": "user", "content": "¿Cuántos años tienes?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic question about age using tener.\", \"grammar\": [\"Present Indicative\", \"Tener for Age\"]}"},
                                                {"role": "user", "content": "Quiero ir al cine, pero tengo mucho sueño."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Connector pero linking a desire and the idiomatic expression tener sueño.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "No fui a la fiesta porque estaba enferma."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Causal clause using porque with simple past tenses (Preterite and Imperfect).\", \"grammar\": [\"Preterite Indefinite\", \"Imperfect Indicative\", \"Causal Connector porque\"]}"},
                                                {"role": "user", "content": "Hemos comido en casa de mis padres esta noche."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect tense for a completed action within a current/recent timeframe.\", \"grammar\": [\"Present Perfect Indicative\"]}"},
                                                {"role": "user", "content": "Cuando voy a España, siempre hablo español."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Temporal clause using cuando with present tense for habitual actions.\", \"grammar\": [\"Temporal Connector cuando\", \"Present Indicative\"]}"},
                                                {"role": "user", "content": "Voy a comprar un regalo mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Future periphrasis using ir a + infinitive.\", \"grammar\": [\"Ir a + Infinitive\"]}"},
                                                {"role": "user", "content": "Tenemos que estudiar el vocabulario para la prueba."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Obligation using tener que + infinitive.\", \"grammar\": [\"Tener que + Infinitive\"]}"},
                                                {"role": "user", "content": "Puedes llamarme cuando llegues al aeropuerto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Modal verb poder + infinitive and temporal clause with present indicative (future reference is B2).\", \"grammar\": [\"Poder + Infinitive\", \"Present Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Ayer fui al gimnasio, pero hoy estoy cansada."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Contrast using pero between Preterite and Present/Estar.\", \"grammar\": [\"Preterite Indefinite\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Me gustaría visitar México el próximo verano."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Polite wish without que is official B1.\", \"grammar\": [\"Conditional Present\", \"Infinitive\"]}"},
                                                {"role": "user", "content": "Acabo de terminar mi proyecto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Immediate past action using acabar de + infinitive.\", \"grammar\": [\"Acabar de + Infinitive\"]}"},
                                                {"role": "user", "content": "Debemos salir ahora o llegaremos tarde."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Obligation using deber + infinitive, linked by the connector o.\", \"grammar\": [\"Deber + Infinitive\", \"Simple Future\", \"Connector o\"]}"},
                                                {"role": "user", "content": "Tengo mucha sed."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Idiomatic expression for thirst using tener sed.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\"]}"},
                                                {"role": "user", "content": "La semana pasada, vi una película muy triste."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Preterite indefinido with a specific time marker.\", \"grammar\": [\"Preterite Indefinite\"]}"},
                                                {"role": "user", "content": "No sabe nadar, pero quiere aprender."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Ability using saber + infinitive, contrasted with desire.\", \"grammar\": [\"Saber + Infinitive\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "A las diez, estábamos en la cama."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Imperfect tense for a state or condition in the past.\", \"grammar\": [\"Imperfect Indicative\"]}"},
                                                {"role": "user", "content": "Cerraron el parque cuando empezó a llover."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Temporal clause using cuando linking two simple past actions (Preterite and Imperfect).\", \"grammar\": [\"Preterite Indefinite\", \"Imperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Hay que comprar más leche para el desayuno."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Impersonal obligation using hay que + infinitive.\", \"grammar\": [\"Hay que + Infinitive\"]}"},
                                                {"role": "user", "content": "No tengo dinero, por lo que no puedo ir."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple consequence connector por lo que (or porque) linking two present tense clauses.\", \"grammar\": [\"Present Indicative\", \"Consequence Connector\"]}"},
                                                {"role": "user", "content": "¿Qué has hecho hoy?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Basic question using the present perfect.\", \"grammar\": [\"Present Perfect Indicative\", \"Question Formation\"]}"},
                                                {"role": "user", "content": "Ayer hacía sol, pero hoy llueve."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Contrast using pero between Imperfect and Present tense.\", \"grammar\": [\"Imperfect Indicative\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "La próxima semana iré a visitar a mi tío."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple future tense for a planned action.\", \"grammar\": [\"Simple Future\"]}"},
                                                {"role": "user", "content": "Siempre vamos a la playa cuando hace buen tiempo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Habitual action linked by cuando (Present Indicative).\", \"grammar\": [\"Temporal Connector cuando\", \"Present Indicative\"]}"},
                                                {"role": "user", "content": "Estoy viendo la televisión ahora mismo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present progressive periphrasis.\", \"grammar\": [\"Estar + Gerund\"]}"},
                                                {"role": "user", "content": "Tengo mucho frío en esta habitación."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Idiomatic expression for cold using tener frío.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\"]}"},
                                                {"role": "user", "content": "Me da rabia que no me escuchen cuando hablo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion expression ('Me da rabia') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Es importante que sepas esto antes de irte."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Impersonal evaluative expression requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Cuando era estudiante, estudiaba mucho y salía poco."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect tense used for habitual past actions and description.\", \"grammar\": [\"Imperfect Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Fuimos a cenar, pero no habíamos reservado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Contrast between Preterite and Pluperfect Indicative, narrative sequencing.\", \"grammar\": [\"Preterite Indefinite\", \"Pluperfect Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Ojalá que no tengamos que esperar mucho."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Wish expression using ojalá + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Ojalá + Present Subjunctive\"]}"},
                                                {"role": "user", "content": "He trabajado en esta empresa desde 2020."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect tense used for duration up to the present.\", \"grammar\": [\"Present Perfect Indicative\", \"Duration desde\"]}"},
                                                {"role": "user", "content": "Busco un trabajo que me permita viajar."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative clause with indefinite antecedent requiring present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},
                                                {"role": "user", "content": "No creo que sea una buena idea."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Doubt/negated opinion requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Me parece que no te has dado cuenta del error."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Opinion clause with Present Perfect Indicative (no subjunctive trigger).\", \"grammar\": [\"Present Perfect Indicative\", \"Opinion Clause\"]}"},
                                                {"role": "user", "content": "Me alegro de que estés aquí sano y salvo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb ('alegrarse') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Me gustaría ir al banco mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Polite request using conditional me gustaría + infinitive.\", \"grammar\": [\"Me gustaría + Infinitive\"]}"},
                                                {"role": "user", "content": "Es una pena que no hayas podido venir."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Impersonal evaluative expression ('Es una pena') requiring the present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Cuando llegué a casa, mi madre ya había salido."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Past sequence contrasting Preterite with Pluperfect Indicative.\", \"grammar\": [\"Preterite Indefinite\", \"Pluperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Estaba lloviendo cuando salimos del teatro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect for ongoing action/description contrasted with Preterite for sudden action.\", \"grammar\": [\"Imperfect Indicative\", \"Preterite Indefinite\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Aunque me duele la rodilla, voy a correr."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Concessive clause using aunque + present indicative (real concession).\", \"grammar\": [\"Present Indicative\", \"Concessive Connector aunque\"]}"},
                                                {"role": "user", "content": "Pensaba que vendrías, pero no has llamado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Contrast using pero between Imperfect and Present Perfect.\", \"grammar\": [\"Imperfect Indicative\", \"Present Perfect Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Hace un mes que no nos vemos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Duration up to the present using hace + time + que + negative present.\", \"grammar\": [\"Present Indicative\", \"Duration hace que\"]}"},
                                                {"role": "user", "content": "Quiero que me digas la verdad."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Volition verb ('querer') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Volition Clause\"]}"},
                                                {"role": "user", "content": "Te llamaré cuando termine la reunión."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Future action linked by cuando + Future Tense (future subjunctive is B2).\", \"grammar\": [\"Simple Future\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Es dudoso que aprueben la nueva ley."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Doubt expression ('Es dudoso que') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "El tren saldrá pronto, creo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Simple future tense for a prediction.\", \"grammar\": [\"Simple Future\"]}"},
                                                {"role": "user", "content": "Cuando vivía en Málaga, hacía mucho calor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect tense for past description/habit.\", \"grammar\": [\"Imperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Me sorprende que no hayas estado nunca aquí."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + Present Perfect Subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Es posible que hayamos olvidado algo en casa."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Possibility expression ('Es posible que') requiring the present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Mi jefe quería que le entregara el informe hoy."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Volition verb ('quería que') requiring the imperfect subjunctive (B2).\", \"grammar\": [\"Imperfect Subjunctive\", \"Volition Clause\"]}"},
                                                {"role": "user", "content": "Tengo un coche, pero es viejo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple possession and description linked by the connector pero.\", \"grammar\": [\"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "El perro es grande y la casa es pequeña."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple descriptions using ser, linked by the connector y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "El libro está cerrado o está abierto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple description of state using estar, linked by the connector o.\", \"grammar\": [\"Present Indicative\", \"Connector o\"]}"},
                                                {"role": "user", "content": "Vivo en Barcelona y mi oficina está en el centro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple actions and locations using vivir and estar, linked by y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Quiero comprar pan, por favor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic request using querer + infinitive.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Mi hermana tiene un trabajo nuevo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple possession using tener.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Me gusta el color azul."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic expression of taste with gustar.\", \"grammar\": [\"Present Indicative\"]}"},
                                                {"role": "user", "content": "Ella es médica y trabaja mucho."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple identity and habitual action using ser and trabajar, linked by y.\", \"grammar\": [\"Present Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Necesito agua o zumo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Simple necessity using necesitar and the connector o.\", \"grammar\": [\"Present Indicative\", \"Connector o\"]}"},
                                                {"role": "user", "content": "¿Cuántos años tienes?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A1\", \"reasoning\": \"Basic question about age using tener.\", \"grammar\": [\"Present Indicative\", \"Tener for Age\"]}"},
                                                {"role": "user", "content": "Quiero ir al cine, pero tengo mucho sueño."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Connector pero linking a desire and the idiomatic expression tener sueño.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "No fui a la fiesta porque estaba enferma."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Causal clause using porque with simple past tenses (Preterite and Imperfect).\", \"grammar\": [\"Preterite Indefinite\", \"Imperfect Indicative\", \"Causal Connector porque\"]}"},
                                                {"role": "user", "content": "Hemos comido en casa de mis padres esta noche."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present perfect tense for a completed action within a current/recent timeframe.\", \"grammar\": [\"Present Perfect Indicative\"]}"},
                                                {"role": "user", "content": "Cuando voy a España, siempre hablo español."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Temporal clause using cuando with present tense for habitual actions.\", \"grammar\": [\"Temporal Connector cuando\", \"Present Indicative\"]}"},
                                                {"role": "user", "content": "Voy a comprar un regalo mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Future periphrasis using ir a + infinitive.\", \"grammar\": [\"Ir a + Infinitive\"]}"},
                                                {"role": "user", "content": "Tenemos que estudiar el vocabulario para la prueba."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Obligation using tener que + infinitive.\", \"grammar\": [\"Tener que + Infinitive\"]}"},
                                                {"role": "user", "content": "Puedes llamarme cuando llegues al aeropuerto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Modal verb poder + infinitive and temporal clause with present indicative.\", \"grammar\": [\"Poder + Infinitive\", \"Present Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Ayer fui al gimnasio, pero hoy estoy cansada."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Contrast using pero between Preterite and Present/Estar.\", \"grammar\": [\"Preterite Indefinite\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Acabo de terminar mi proyecto."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Immediate past action using acabar de + infinitive.\", \"grammar\": [\"Acabar de + Infinitive\"]}"},
                                                {"role": "user", "content": "Debemos salir ahora o llegaremos tarde."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Obligation using deber + infinitive, linked by the connector o.\", \"grammar\": [\"Deber + Infinitive\", \"Simple Future\", \"Connector o\"]}"},
                                                {"role": "user", "content": "Tengo mucha sed."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Idiomatic expression for thirst using tener sed.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\"]}"},
                                                {"role": "user", "content": "La semana pasada, vi una película muy triste."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Preterite indefinido with a specific time marker.\", \"grammar\": [\"Preterite Indefinite\"]}"},
                                                {"role": "user", "content": "No sabe nadar, pero quiere aprender."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Ability using saber + infinitive, contrasted with desire.\", \"grammar\": [\"Saber + Infinitive\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "A las diez, estábamos en la cama."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Imperfect tense for a state or condition in the past.\", \"grammar\": [\"Imperfect Indicative\"]}"},
                                                {"role": "user", "content": "Cerraron el parque cuando empezó a llover."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Temporal clause using cuando linking two simple past actions (Preterite and Imperfect).\", \"grammar\": [\"Preterite Indefinite\", \"Imperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Hay que comprar más leche para el desayuno."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Impersonal obligation using hay que + infinitive.\", \"grammar\": [\"Hay que + Infinitive\"]}"},
                                                {"role": "user", "content": "No tengo dinero, por lo que no puedo ir."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple consequence connector por lo que (or porque) linking two present tense clauses.\", \"grammar\": [\"Present Indicative\", \"Consequence Connector\"]}"},
                                                {"role": "user", "content": "¿Qué has hecho hoy?"},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Basic question using the present perfect.\", \"grammar\": [\"Present Perfect Indicative\", \"Question Formation\"]}"},
                                                {"role": "user", "content": "Ayer hacía sol, pero hoy llueve."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Contrast using pero between Imperfect and Present tense.\", \"grammar\": [\"Imperfect Indicative\", \"Present Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "La próxima semana iré a visitar a mi tío."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Simple future tense for a planned action.\", \"grammar\": [\"Simple Future\"]}"},
                                                {"role": "user", "content": "Siempre vamos a la playa cuando hace buen tiempo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Habitual action linked by cuando (Present Indicative).\", \"grammar\": [\"Temporal Connector cuando\", \"Present Indicative\"]}"},
                                                {"role": "user", "content": "Estoy viendo la televisión ahora mismo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Present progressive periphrasis.\", \"grammar\": [\"Estar + Gerund\"]}"},
                                                {"role": "user", "content": "Tengo mucho frío en esta habitación."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"A2\", \"reasoning\": \"Idiomatic expression for cold using tener frío.\", \"grammar\": [\"Present Indicative\", \"Idiomatic tener\"]}"},
                                                {"role": "user", "content": "Me da rabia que no me escuchen cuando hablo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion expression ('Me da rabia') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Es importante que sepas esto antes de irte."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Impersonal evaluative expression requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Cuando era estudiante, estudiaba mucho y salía poco."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect tense used for habitual past actions and description.\", \"grammar\": [\"Imperfect Indicative\", \"Connector y\"]}"},
                                                {"role": "user", "content": "Fuimos a cenar, pero no habíamos reservado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Contrast between Preterite and Pluperfect Indicative, narrative sequencing.\", \"grammar\": [\"Preterite Indefinite\", \"Pluperfect Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Ojalá que no tengamos que esperar mucho."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Wish expression using ojalá + present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Ojalá + Present Subjunctive\"]}"},
                                                {"role": "user", "content": "He trabajado en esta empresa desde 2020."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Present perfect tense used for duration up to the present.\", \"grammar\": [\"Present Perfect Indicative\", \"Duration desde\"]}"},
                                                {"role": "user", "content": "Busco un trabajo que me permita viajar."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Relative clause with indefinite antecedent requiring present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Relative Subjunctive\"]}"},
                                                {"role": "user", "content": "No creo que sea una buena idea."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Doubt/negated opinion requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Me parece que no te has dado cuenta del error."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Opinion clause with Present Perfect Indicative (no subjunctive trigger).\", \"grammar\": [\"Present Perfect Indicative\", \"Opinion Clause\"]}"},
                                                {"role": "user", "content": "Me alegro de que estés aquí sano y salvo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb ('alegrarse') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Me gustaría ir al banco mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Polite request using conditional me gustaría + infinitive.\", \"grammar\": [\"Conditional Present\"]}"},
                                                {"role": "user", "content": "Es una pena que no hayas podido venir."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Impersonal evaluative expression ('Es una pena') requiring the present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Cuando llegué a casa, mi madre ya había salido."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Past sequence contrasting Preterite with Pluperfect Indicative.\", \"grammar\": [\"Preterite Indefinite\", \"Pluperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Estaba lloviendo cuando salimos del teatro."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect for ongoing action/description contrasted with Preterite for sudden action.\", \"grammar\": [\"Imperfect Indicative\", \"Preterite Indefinite\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Aunque me duele la rodilla, voy a correr."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Concessive clause using aunque + present indicative (real concession).\", \"grammar\": [\"Present Indicative\", \"Concessive Connector aunque\"]}"},
                                                {"role": "user", "content": "Pensaba que vendrías, pero no has llamado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Contrast using pero between Imperfect and Present Perfect.\", \"grammar\": [\"Imperfect Indicative\", \"Present Perfect Indicative\", \"Connector pero\"]}"},
                                                {"role": "user", "content": "Hace un mes que no nos vemos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Duration up to the present using hace + time + que + negative present.\", \"grammar\": [\"Present Indicative\", \"Duration hace que\"]}"},
                                                {"role": "user", "content": "Quiero que me digas la verdad."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Volition verb ('querer') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Volition Clause\"]}"},
                                                {"role": "user", "content": "Te llamaré cuando termine la reunión."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Future action linked by cuando + Future Tense.\", \"grammar\": [\"Simple Future\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Es dudoso que aprueben la nueva ley."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Doubt expression ('Es dudoso que') requiring the present subjunctive.\", \"grammar\": [\"Present Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "El tren saldrá pronto, creo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Simple future tense for a prediction.\", \"grammar\": [\"Simple Future\"]}"},
                                                {"role": "user", "content": "Cuando vivía en Málaga, hacía mucho calor."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Imperfect tense for past description/habit.\", \"grammar\": [\"Imperfect Indicative\", \"Temporal Connector cuando\"]}"},
                                                {"role": "user", "content": "Me sorprende que no hayas estado nunca aquí."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Emotion verb + Present Perfect Subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Emotion / Doubt Verb + que\"]}"},
                                                {"role": "user", "content": "Es posible que hayamos olvidado algo en casa."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B1\", \"reasoning\": \"Possibility expression ('Es posible que') requiring the present perfect subjunctive.\", \"grammar\": [\"Present Perfect Subjunctive\", \"Evaluative Expression + que\"]}"},
                                                {"role": "user", "content": "Mi jefe quería que le entregara el informe hoy."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Volition verb ('quería que') requiring the imperfect subjunctive (B2).\", \"grammar\": [\"Imperfect Subjunctive\", \"Volition Clause\"]}"},
                                                {"role": "user", "content": "El informe no podrá publicarse sin el preceptivo visto bueno del comité."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression 'visto bueno' and administrative/legal vocabulary 'preceptivo'.\", \"grammar\": [\"Fixed Formal Expression\", \"Administrative Vocabulary\"]}"},
                                                {"role": "user", "content": "A poco que se le insistiere, cedería a la presión."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Future subjunctive ('insistiere') used in a concessive clause.\", \"grammar\": [\"Future Subjunctive\", \"Concessive Clause\"]}"},
                                                {"role": "user", "content": "De no haber contado con su apoyo, el proyecto habría fracasado."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Inverted pluperfect subjunctive construction ('De no haber contado con').\", \"grammar\": [\"Pluperfect Subjunctive\", \"Inverted Conditional\"]}"},
                                                {"role": "user", "content": "Así pues, conviene analizar las consecuencias de dicha medida."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal discourse marker ('Así pues') and sophisticated vocabulary ('conviene').\", \"grammar\": [\"Fixed Formal Expression\", \"Discourse Marker\"]}"},
                                                {"role": "user", "content": "Con todo, aceptaron la propuesta sin reservas."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal adversative connector ('Con todo').\", \"grammar\": [\"Fixed Formal Expression\", \"Adversative Connector\"]}"},
                                                {"role": "user", "content": "En aras de la legalidad, se modificaron las bases del concurso."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression ('En aras de') indicating purpose.\", \"grammar\": [\"Fixed Formal Expression\"]}"},
                                                {"role": "user", "content": "Quiérase o no, esa ideología ha calado en la sociedad."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Impersonal, fixed concessive phrase ('quiérase o no') with the present subjunctive.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},
                                                {"role": "user", "content": "Mal que le pese a los críticos, la ley se aprobó."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal concessive expression ('Mal que le pese') using the present subjunctive.\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},
                                                {"role": "user", "content": "La solución se implementará, sea cual fuere el coste."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal concessive expression ('sea cual fuere').\", \"grammar\": [\"Fixed Formal Expression\", \"Present Subjunctive\"]}"},
                                                {"role": "user", "content": "Ni por asomo creímos que el suceso pudiera repetirse."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Strong idiomatic negation ('Ni por asomo') combined with the imperfect subjunctive.\", \"grammar\": [\"Fixed Idiomatic Expression\", \"Imperfect Subjunctive\"]}"},
                                                {"role": "user", "content": "A la postre, la decisión resultó ser la más acertada."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Literary temporal expression ('A la postre').\", \"grammar\": [\"Fixed Formal Expression\", \"Temporal Expression\"]}"},
                                                {"role": "user", "content": "El acusado no hube de responder a las acusaciones más graves."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Pretérito anterior ('hube de responder').\", \"grammar\": [\"Preterite Anterior\"]}"},
                                                {"role": "user", "content": "Habida cuenta de su historial, la sentencia fue indulgente."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Fixed formal expression ('Habida cuenta de').\", \"grammar\": [\"Fixed Formal Expression\"]}"},
                                                {"role": "user", "content": "No obstante haber sido advertido, el trabajador prosiguió su tarea."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal use of 'No obstante haber' (gerundive construction) in a concessive phrase.\", \"grammar\": [\"Gerundive Construction\", \"Fixed Formal Expression\"]}"},
                                                {"role": "user", "content": "De haberlo sabido, habría actuado de otra guisa."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Inverted pluperfect subjunctive + high-level vocabulary ('guisa').\", \"grammar\": [\"Pluperfect Subjunctive\", \"Formal Vocabulary\"]}"},
                                                {"role": "user", "content": "La multitud vituperaba al orador, quien se mantuvo impertérrito."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal, low-frequency vocabulary ('vituperaba', 'impertérrito') and relative clause.\", \"grammar\": [\"Formal Vocabulary\", \"Imperfect Indicative\"]}"},
                                                {"role": "user", "content": "Dado el caso de que la ley fuere impugnada, el proceso se alargará."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal conditional structure ('Dado el caso de que') with future subjunctive ('fuere').\", \"grammar\": [\"Fixed Formal Expression\", \"Future Subjunctive\"]}"},
                                                {"role": "user", "content": "Sin el beneplácito del director, la propuesta no prosperará."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal, low-frequency vocabulary ('beneplácito') and future tense.\", \"grammar\": [\"Formal Vocabulary\", \"Simple Future\"]}"},
                                                {"role": "user", "content": "Se sentía vilipendiado por sus compañeros y decidió renunciar."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal, low-frequency vocabulary ('vilipendiado') and sophisticated emotional register.\", \"grammar\": [\"Formal Vocabulary\", \"Preterite Indefinite\"]}"},
                                                {"role": "user", "content": "El escrito debe redactarse con toda pulcritud."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"C1\", \"reasoning\": \"Formal administrative language ('debe redactarse') and low-frequency abstract noun ('pulcritud').\", \"grammar\": [\"Formal Vocabulary\", \"Periphrasis of Obligation\"]}"},
                                                {"role": "user", "content": "Preferiría que me lo contaras mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Conditional preference ('Preferiría') requiring the imperfect subjunctive ('contaras'), which is a core B2 trigger.\", \"grammar\": [\"Conditional Present\", \"Imperfect Subjunctive\"]}"},
                                                {"role": "user", "content": "Me gustaría que me ayudaras mañana."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Polite request ('Me gustaría') requiring the imperfect subjunctive ('ayudaras'), which is a core B2 trigger.\", \"grammar\": [\"Conditional Present\", \"Imperfect Subjunctive\"]}"},
                                                {"role": "user", "content": "Preferiría que me lo explicaras con calma."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Conditional preference ('Preferiría') requiring the imperfect subjunctive ('explicaras'), which is a core B2 trigger.\", \"grammar\": [\"Conditional Present\", \"Imperfect Subjunctive\"]}"},
                                                {"role": "user", "content": "Querría que me acompañaras al médico."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Conditional desire ('Querría') requiring the imperfect subjunctive ('acompañaras'), which is a core B2 trigger.\", \"grammar\": [\"Conditional Present\", \"Imperfect Subjunctive\"]}"},
                                                {"role": "user", "content": "Buscaba un piso que fuera tranquilo."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Past description ('Buscaba') requiring the imperfect subjunctive ('fuera') in a relative clause.\", \"grammar\": [\"Imperfect Subjunctive\", \"Relative Subjunctive\"]}"},
                                                {"role": "user", "content": "Quería un profesor que ayudara a todos."},
                                                {"role": "assistant", "content": "{\"cefr_level\": \"B2\", \"reasoning\": \"Past desire ('Quería') requiring the imperfect subjunctive ('ayudara') in a relative clause.\", \"grammar\": [\"Imperfect Subjunctive\", \"Relative Subjunctive\"]}"},
"""

# --- 3. EXECUTION LOGIC ---
OUTPUT_FILE = 'spanish_classification_data_FINAL_CLEAN.jsonl'
processed_lines = []

# Regex to find consecutive USER and ASSISTANT JSON objects.
# It captures the full content strings, including internal escaped quotes.
# This pattern is robust against extra whitespace and newlines between the pairs.
PAIR_REGEX = re.compile(
    r'\{\s*"role":\s*"user",\s*"content":\s*"(.*?)"\s*\},?\s*'  # User object
    r'\{\s*"role":\s*"assistant",\s*"content":\s*"(.*?)"\s*\}',  # Assistant object
    re.DOTALL
)

matches = PAIR_REGEX.findall(FEWSHOTS_BLOCK)
total_matches = len(matches)

if total_matches == 0:
    print("\n❌ CRITICAL FAILURE: Could not match any User/Assistant pairs. Check internal quote escaping in FEWSHOTS_BLOCK.")
    # Attempt to diagnose if the entire block is wrapped in quotes
    if FEWSHOTS_BLOCK.strip().startswith('"'):
        print("HINT: Ensure your FEWSHOTS_BLOCK variable does NOT have an outer set of quotes or redundant escapes.")
    exit()


# Process each matched pair
for user_content_raw, assistant_content_raw in matches:
    try:
        # 1. Clean the captured strings: fix double-escaped quotes and trim whitespace
        user_content = user_content_raw.replace('\\\\"', '"').strip()
        assistant_content = assistant_content_raw.replace('\\\\"', '"').strip()

        # 2. Re-create the final conversation structure (System + User + Assistant)
        conversation = [
            {"role": "system", "content": FULL_SYSTEM_PROMPT_CONTENT.strip()},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
        
        # 3. Append as a JSONL object
        processed_lines.append({"conversations": conversation})

    except Exception as e:
        print(f"Skipping line due to unexpected error: {e}")
        continue

# Write to the final JSONL file
print(f"Writing {len(processed_lines)} clean examples to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
    for line in processed_lines:
        json.dump(line, outfile, ensure_ascii=False)
        outfile.write('\n')

print(f"\n✅ Conversion Complete. Total clean examples: {len(processed_lines)}")
print(f"File saved as {OUTPUT_FILE}. Ready for Google Colab.")