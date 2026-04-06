import PyPDF2
import re
import numpy as np
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn

# Scarica i dati linguistici necessari (lo fa solo la prima volta)
nltk.download('wordnet')
nltk.download('omw-1.4')

# 1. Configurazione MongoDB
URI_MONGO = "mongodb://localhost:64820/?directConnection=true"
NOME_DB = "semantic_engine"
NOME_COLLECTION = "wordV3"  # Spazio vettoriale a 2925 dimensioni "esplicite"

# 2. Estrazione delle parole dal PDF (come prima)
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
total_words = len(words)
print(f"Estratte {total_words} parole uniche.")

# 3. Funzione Motore Semantico Basato su Ontologia
def calcola_similarita_ontologica(parola1, parola2):

    print(f"Calcolando similarità tra '{parola1}' e '{parola2}'...")

    """Calcola la vicinanza usando alberi logici e antonimi."""
    if parola1 == parola2:
        return 1.0
        
    synsets1 = wn.synsets(parola1)
    synsets2 = wn.synsets(parola2)
    
    if not synsets1 or not synsets2:
        return 0.0 # Parola non trovata in WordNet
        
    # A. CONTROLLO ANTONIMI (Es. good vs bad -> -1.0)
    for syn1 in synsets1:
        for lemma1 in syn1.lemmas():
            for ant in lemma1.antonyms():
                for syn2 in synsets2:
                    if ant in syn2.lemmas():
                        return -1.0
                        
    # B. CONTROLLO SIMILARITÀ GERARCHICA (Wu-Palmer Similarity)
    # Trova il percorso più breve nell'albero concettuale (es. dog -> animal)
    max_sim = 0.0
    for s1 in synsets1:
        for s2 in synsets2:
            # WUP calcola la profondità nell'albero genealogico delle parole
            sim = s1.wup_similarity(s2)
            if sim and sim > max_sim:
                max_sim = sim
                
    # C. SOGLIA DI NEUTRALITÀ
    # WordNet dà valori bassi (es. 0.1) anche a cose slegate. 
    # Portiamo a 0 tutto ciò che ha una similarità debole per avere vettori sparsi e puliti.
    if max_sim < 0.25:
        return 0.0
        
    return round(max_sim, 3)

# 4. Creazione della Matrice ESA (Explicit Semantic Analysis)
print("Generazione della matrice semantica 2925x2925 in corso...")
print("Attenzione: richiederà qualche minuto (circa 8.5 milioni di controlli logici)...")

documenti = []
for i, parola_target in enumerate(words):
    print(f"\nParola target: '{parola_target}' ({i + 1}/{total_words})")
    vettore_esplicito = []
    
    for parola_riferimento in words:
        score = calcola_similarita_ontologica(parola_target, parola_riferimento)
        vettore_esplicito.append(score)
        
    documenti.append({
        "word": parola_target,
        "vector": vettore_esplicito
    })
    
    if (i + 1) % 50 == 0:
        print(f"Processate {i + 1} parole su {total_words}...")

# 5. Inserimento in MongoDB
print(f"\nConnessione a {URI_MONGO}...")
client = MongoClient(URI_MONGO)
db = client[NOME_DB]
collection = db[NOME_COLLECTION]

print(f"Inserimento dei mega-vettori in {NOME_COLLECTION}...")
if documenti:
    collection.insert_many(documenti)
    print("✅ Creazione dello Spazio Semantico Perfetto completata!")
else:
    print("❌ Errore nella generazione dei documenti.")

client.close()