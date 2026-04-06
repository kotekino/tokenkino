import spacy
import PyPDF2
import re
import numpy as np
from pymongo import MongoClient

# 1. Configurazione MongoDB
URI_MONGO = "mongodb://localhost:64820/?directConnection=true"
NOME_DB = "semantic_engine"
NOME_COLLECTION = "baseV2"  # Nuova collection per gli embedding nativi

# 2. Estrazione delle parole dal PDF
words = []
print("Estrazione parole dal PDF...")
with open('The_Oxford_3000.pdf', 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    for page in reader.pages:
        text = page.extract_text()
        for line in text.split('\n'):
            line = line.strip()
            if not line: continue
            
            m = re.match(r'^([a-zA-Z-]+)\s+.*[A-C][1-2]$', line)
            if m:
                words.append(m.group(1).lower())
            else:
                parts = line.split()
                if len(parts) >= 3 and parts[-1] in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
                    word = re.sub(r'[^a-z-]', '', parts[0].lower())
                    if word: words.append(word)

words = list(dict.fromkeys(words))
print(f"Estratte {len(words)} parole uniche.")

# 3. Caricamento del modello NLP e generazione vettori
print("Caricamento modello spaCy (en_core_web_md)...")
nlp = spacy.load("en_core_web_md", disable=["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer", "ner"])

print("Generazione degli embedding in corso...")
tokens = list(nlp.pipe(words))

# Prepariamo i documenti per l'inserimento
documenti = []
for i, token in enumerate(tokens):
    if token.has_vector:
        # Usiamo il vettore reale da 300 dimensioni
        vector = token.vector.tolist()
    else:
        # Vettore nullo se la parola non è nel vocabolario del modello
        vector = [0.0] * 300
    
    documenti.append({
        "word": words[i],
        "vector": vector
    })

# 4. Inserimento in MongoDB
print(f"Connessione a {URI_MONGO}...")
client = MongoClient(URI_MONGO)
db = client[NOME_DB]
collection = db[NOME_COLLECTION]

# Pulizia preventiva (opzionale, se vuoi resettare la wordV2 ogni volta che lanci lo script)
# collection.delete_many({}) 

print(f"Inserimento di {len(documenti)} documenti in {NOME_COLLECTION}...")
if documenti:
    collection.insert_many(documenti)
    print("✅ Ingestione completata con successo!")
else:
    print("❌ Nessun documento da inserire.")

client.close()