import pandas as pd
from qwen import analyzer
from diagnostic_dashboard import diagnostic_dashboard
import time

# --- Load shards ---
files = [
    "vocaba.english.csv"
]
dfs = [pd.read_csv(f) for f in files]

# --- Normalize columns ---
for df in dfs:
    df.rename(columns={"cefr_level": "previous_predicted", "translation": "sentence"}, inplace=True)

df = pd.concat(dfs, ignore_index=True)

# --- Corrections to build expected ground truth ---
corrections = {
    "Voy a llevar mi coche.": "B1",
    "Lo encontrarás en una ferretería.": "B1",
    "Pensé que era verdad.": "B1",
    "Ellos discutieron.": "B1",
    "Comí caviar.": "B1",
    "Tomaste la llave equivocada.": "B1",
    "Logré entrar.": "B1",
    "¡Lo esperaba!": "B1",
    "Voy a tomar un baño.": "B1",
    "Salimos en tren.": "B1",
    "Ella llevaba un sombrero negro.": "B1",
    "¡Sí! ¡Gané dos veces seguidas!": "B1",
    "Tengo que irme a dormir.": "A2",
    "Deberías dormir.": "A2",
    "Tengo que irme a la cama.": "A2",
    "Los llamaré mañana cuando regrese.": "B2",
    "No abras antes de que el tren se detenga.": "B2",
    "Haz lo que él te diga.": "B2",
    "Lo siento, no creo que pueda.": "B2",
    "Estoy vivo aunque no estoy dando ninguna señal de vida.": "B2",
    "Diles que me llamen antes de que se vayan.": "B2",
    "Este es el pueblo del que te hablé.": "B2",
    "Este es el chico en el que pienso.": "B2",
    "Se le ha advertido en varias ocasiones.": "B2",
    "No estoy convencido en absoluto.": "B2",
    "Es demasiado bueno para ser verdad.": "B2",
    "No le escuches, está hablando tonterías.": "B2",
    "No te puedes perder en las grandes ciudades; ¡hay mapas por todas partes!": "B2",
    "Estaba lloviendo cuando salimos, pero para cuando llegamos, hacía sol.": "B2",
    "Si comes demasiado, te volverás gordo.": "B2",
    "Sabía que él aceptaría.": "B2",
    "Ella vendría gustosamente, pero estaba de vacaciones.": "B2",
    "¿Cómo puedes tener una laptop y no un teléfono celular?": "B2",
    "Poco a poco, notarás mejoras en tus escritos.": "B2",
    "Cuanto antes, mejor.": "B2",
    "El estudiante decidió resumir su trabajo eliminando detalles innecesarios.": "C1",
    "El líder del gremio relegó a Vince a un cargo menor porque estaba abusando de su poder.": "C1",
    "James tenía un gran miedo a cometer errores en clase y ser reprendido.": "C1",
    "El director reprendía severamente a los estudiantes cada vez que hacían un desorden en el pasillo.": "C1",
    "Tim es un gran fan de la comedia satírica.": "C1",
    "La madre de Spenser a menudo lo examina por cada pequeño error que comete.": "C1",
    "Las funciones seno y coseno toman valores entre -1 y 1 (incluyendo -1 y 1).": "C2",
    "Estoy en contra de usar la muerte como castigo. También estoy en contra de usarla como recompensa.": "C2",
    "La segunda mitad de la vida de un hombre está compuesta únicamente por los hábitos que ha adquirido durante la primera mitad.": "C2",
    "Según un nuevo informe, las niñas tienen más probabilidades que los niños de estar desnutridas, sufrir pobreza, enfrentar violencia y ser privadas de educación.": "C2",
    "El 18 de mayo, una joven pareja japonesa fue arrestada después de que su bebé de un año fuera encontrado envuelto en una bolsa de plástico y arrojado en una cuneta.": "C2",
    "Estamos atormentados por una vida ideal, y es porque llevamos dentro de nosotros el comienzo y la posibilidad de alcanzarla.": "C2",
    "La muerte es solo un horizonte, y un horizonte no es más que el límite de nuestra vista.": "C2",
    "La teoría científica que más me gusta es que los anillos de Saturno están compuestos enteramente de equipaje perdido.": "C2",
    "Depende de lo que quieras decir con 'creer' en Dios.": "C2",
    "Las ideas de Freud sobre el comportamiento humano lo llevaron a ser reconocido como un pensador profundo.": "C2",
    "Las personas ciegas a veces desarrollan una habilidad compensatoria para percibir la proximidad de los objetos que las rodean.": "C2",
    "No quiero escuchar más de tus quejas.": "A2",
    "Quiero ser más independiente.": "A2",
    "Estoy embarazada de cuatro meses.": "A2",
    "Tengo un sapo en la garganta.": "A2",
    "Siéntete como en casa.": "A2",
    "Cuesta un ojo de la cara.": "A2",
    "El que ríe último, ríe mejor.": "A2",
    "Más vale tarde que nunca.": "A2",
    "De tal palo, tal astilla.": "A2",
    "A quien madruga, Dios le ayuda.": "A2",
}

# --- Build expected (fallback to previous_predicted when no correction exists) ---
df["expected"] = df.apply(
    lambda row: corrections.get(row["sentence"], row["previous_predicted"]),
    axis=1
)

# --- Run analyzer with ticker ---
import_results = []
total = len(df)

for i, row in df.iterrows():
    predicted, reasoning = analyzer(row["sentence"])  # analyzer now returns (level, reasoning)
    import_results.append({
        "sentence": row["sentence"],
        "expected": row["expected"],
        "predicted": predicted,
        "reasoning": reasoning
    })
    if (i+1) % 50 == 0 or (i+1) == total:
        print(f"Processed {i+1}/{total}")

print(f"\nFinished processing {total} rows.")

# --- Optional harness sanity check ---
test_results = [
    {"expected": "A1", "predicted": analyzer("Tengo un gato.")[0]},
    {"expected": "B2", "predicted": analyzer("Aunque estaba cansado, terminé el proyecto.")[0]},
    {"expected": "C1", "predicted": analyzer("Si hubiera tenido más tiempo, habría viajado a Italia.")[0]},
    {"expected": "C2", "predicted": analyzer("La epistemología cuestiona los fundamentos del conocimiento humano.")[0]},
]

# --- Evaluate ---
diagnostic_dashboard(test_results, import_results)

# --- Save labeled run for auditability ---
df["predicted"] = [r["predicted"] for r in import_results]
df["reasoning"] = [r["reasoning"] for r in import_results]
df.to_csv("shards_labeled_run.csv", index=False)
print("Saved: shards_labeled_run.csv")

def compare_daily_runs(df):
    # Consistency across all sentences
    consistency = (df["predicted"] == df["previous_predicted"]).mean()
    print(f"Consistency vs yesterday: {consistency:.2%}")

    # Corrected subset only
    corrected = df[df["sentence"].isin(corrections.keys())]

    improved_cases = corrected[
        (corrected["predicted"] == corrected["expected"]) &
        (corrected["previous_predicted"] != corrected["expected"])
    ]

    regressed_cases = corrected[
        (corrected["predicted"] != corrected["expected"]) &
        (corrected["previous_predicted"] == corrected["expected"])
    ]

    print(f"Improvement rate: {len(improved_cases)}/{len(corrected)} = {len(improved_cases)/len(corrected):.2%}")
    print(f"Regression rate: {len(regressed_cases)}/{len(corrected)} = {len(regressed_cases)/len(corrected):.2%}")

    # Show reasoning snippets for audit
    print("\n--- Improvements ---")
    for _, row in improved_cases.iterrows():
        print(f"Sentence: {row['sentence']}")
        print(f"Yesterday: {row['previous_predicted']} | Today: {row['predicted']} | Expected: {row['expected']}")
        print(f"Reasoning: {row['reasoning']}\n")

    print("\n--- Regressions ---")
    for _, row in regressed_cases.iterrows():
        print(f"Sentence: {row['sentence']}")
        print(f"Yesterday: {row['previous_predicted']} | Today: {row['predicted']} | Expected: {row['expected']}")
        print(f"Reasoning: {row['reasoning']}\n")

compare_daily_runs(df)