import pymongo
import spacy

# 1. Carica il modello spaCy standard (Medium o Large per avere veri vettori)
print("Caricamento del modello spaCy standard (en_core_web_md)...")
nlp = spacy.load("en_core_web_lg")

# 2. Connessione a MongoDB
MONGO_URI = "mongodb://localhost:27018/?directConnection=true"
client = pymongo.MongoClient(MONGO_URI)
db = client['tokeniko']
collection = db['markers'] # La tua collection 'markers'
print("Connessione a MongoDB stabilita.")

# 3. Recupera tutti i documenti presenti nella collection
print("Recupero dei marker dal database...")
all_markers = list(collection.find({}))
print(f"Trovati {len(all_markers)} marker da elaborare.")

count_aggiornati = 0

# 4. Ciclo di replace dei vettori
print("\nInizio aggiornamento dei vettori vettoriali...")
for doc in all_markers:
    word = doc.get("word")
    if not word:
        continue
        
    # Calcola il vettore con spaCy standard
    spacy_doc = nlp(word)
    
    # Verifichiamo che spaCy abbia estratto un vettore valido
    if len(spacy_doc) > 0 and spacy_doc[0].has_vector:
        # Convertiamo l'array NumPy in una lista nativa Python per MongoDB
        new_vector = spacy_doc[0].vector.tolist()
        
        # Facciamo il replace del solo campo 'vector' usando l'__id originale
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"vector": new_vector}}
        )
        count_aggiornati += 1
    else:
        print(f"⚠️ Attenzione: spaCy non ha trovato un vettore statico per la parola: '{word}'")

print(f"\nMigrazione completata con successo! Sostituiti i vettori per {count_aggiornati}/{len(all_markers)} marker.")