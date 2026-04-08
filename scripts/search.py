import pymongo
import numpy as np

# 1. Configurazione: Connessione a MongoDB
# MONGO_URI = "mongodb+srv://kotekino:Lenrek973to!@tokenkino.45wzpkm.mongodb.net/"
# DB_NAME = "tokenkino"
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
NOME_COLLECTION = "dictionary"
NOME_VECTOR_INDEX = "vector_index" # <--- Inserisci il nome del tuo indice su Atlas

# Connessione veloce con timeout
print("Tentativo di connessione a MongoDB...")
client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

try:
    client.admin.command('ping')
except Exception as e:
    print("\n❌ IMPOSSIBILE CONNETTERSI AL DATABASE.")
    print(f"Errore: {e}")
    exit()

db = client[DB_NAME]
collection = db[NOME_COLLECTION]

def ricerca_semantica(frase_input, limit=10):
    print(f"\n🔍 Analisi dell'input: '{frase_input}'")
    
    parole_input = frase_input.lower().split()
    vettori_trovati = []
    parole_trovate = []

    for parola in parole_input:
        documento = collection.find_one({"word": parola})
        
        if documento and "vector" in documento:
            vettori_trovati.append(documento["vector"])
            parole_trovate.append(parola)
        else:
            print(f"  ⚠️ Avviso: La parola '{parola}' non è nel database. Verrà ignorata.")

    if not vettori_trovati:
        print("❌ Nessuna parola valida trovata. Impossibile eseguire la ricerca.")
        return

    print(f"✨ Parole utilizzate per la media: {parole_trovate}")

    matrice_vettori = np.array(vettori_trovati)
    vettore_medio = np.mean(matrice_vettori, axis=0)

    pipeline = [
        {
            "$vectorSearch": {
                "index": NOME_VECTOR_INDEX,
                "path": "vector",
                "queryVector": vettore_medio.tolist(),
                "numCandidates": limit * 10,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 0,
                "word": 1,
                "sense": 1,
                "score": { "$meta": "vectorSearchScore" }
            }
        }
    ]

    print("\n🚀 Risultati trovati:")
    risultati = collection.aggregate(pipeline)
    
    for i, res in enumerate(risultati, 1):
        parola = res.get("word", "Sconosciuta")
        score = res.get("score", 0.0)
        sense = res.get("sense", "Sconosciuto")
        print(f"  {i}. {parola} ({sense}) (Similarity: {score:.4f})")

# ==========================================
# LOOP INTERATTIVO DA TERMINALE
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print(" 🧠 MOTORE DI RICERCA SEMANTICA ATTIVO 🧠")
    print(" Scrivi le parole che vuoi cercare (es. 'good dog').")
    print(" Scrivi 'esci', 'quit' o 'q' per chiudere il programma.")
    print("="*50)

    while True:
        # Prende l'input dall'utente
        test_input = input("\nCosa vuoi cercare? > ").strip()

        # Condizione per uscire dal programma
        if test_input.lower() in ['esci', 'quit', 'q', 'exit']:
            print("Chiusura del motore di ricerca. A presto! 👋")
            break

        # Evita di fare query vuote se premi solo Invio
        if not test_input:
            continue

        # Esegue la ricerca
        ricerca_semantica(test_input, limit=25)
        print("-" * 50)