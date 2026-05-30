import PyPDF2
import re
import numpy as np
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn

# Inizializzazione dati linguistici
nltk.download('wordnet')
nltk.download('omw-1.4')

# 1. Configurazione MongoDB
URI_MONGO = "mongodb://localhost:64820/?directConnection=true"
NOME_DB = "tokenkino"
NOME_COLLECTION = "baseV4"

# 2. Estrazione delle parole dal PDF (Oxford 3000)
def extract_words():
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
    return list(dict.fromkeys(words))

# 3. Motore Semantico Avanzato
def get_semantic_value(parola1, parola2):
    if parola1 == parola2:
        return 1.0
        
    s1 = wn.synsets(parola1)
    s2 = wn.synsets(parola2)
    
    if not s1 or not s2:
        return 0.0

    # A. CONTROLLO SINONIMI ESPLICITI
    # Se condividono almeno un Synset, sono sinonimi (Valore 1.0)
    set1 = set(s1)
    set2 = set(s2)
    if set1.intersection(set2):
        return 1.0

    # B. CONTROLLO ANTONIMI (Valore -1.0)
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for ant in lemma.antonyms():
                if ant.synset() in set2:
                    return -1.0
                        
    # C. DERIVAZIONI MORFOLOGICHE (Risolve able -> ability)
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for drf in lemma.derivationally_related_forms():
                if drf.synset() in set2:
                    return 0.9  # Fortissima correlazione!
                    
    # D. SIMILARITÀ GERARCHICA (WU-PALMER) - CORRETTA
    max_sim = 0.0
    for ss1 in s1:
        for ss2 in s2:
            # Calcoliamo WUP SOLO se le parole condividono la stessa famiglia grammaticale
            if ss1.pos() == ss2.pos():
                sim = ss1.wup_similarity(ss2)
                if sim and sim > max_sim:
                    max_sim = sim
                
    # Soglia molto più severa per evitare falsi positivi (es. abandon vs ability)
    if max_sim > 0.65:
        return round(max_sim, 3)
        
    return 0.0

# 4. Processo principale con salvataggio incrementale
def main():
    words = extract_words()
    total = len(words)
    print(f"Inizio analisi su {total} parole basi per la collection {NOME_COLLECTION}...")

    client = MongoClient(URI_MONGO)
    db = client[NOME_DB]
    collection = db[NOME_COLLECTION]

    for i, target in enumerate(words):
        print(f"\nParola target: '{target}' ({i + 1}/{total})")
        
        # RESUME LOGIC: Controlliamo se la parola è già stata processata
        if collection.find_one({"word": target}):
            # Se vuoi ricalcolare tutto, commenta queste due righe
            # print(f"Skipping {target} (già presente)...")
            continue

        vettore = []
        for base in words:
            valore = get_semantic_value(target, base)
            vettore.append(valore)
        
        # Scrittura immediata su Mongo
        collection.insert_one({
            "word": target,
            "vector": vettore,
            "index": i # Utile per mantenere l'ordine originale degli assi
        })

        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{total} parole completate...")

    print("\n✅ Operazione completata!")
    client.close()

if __name__ == "__main__":
    main()