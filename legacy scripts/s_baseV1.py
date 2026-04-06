import spacy
import PyPDF2
import re

# 1. Estrazione delle parole dal PDF
words = []
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

# 2. Caricamento OTTIMIZZATO del modello NLP
print("Caricamento del modello linguistico (modalità veloce)...")
# Disabilitiamo i componenti che rallentano l'analisi
nlp = spacy.load("en_core_web_md", disable=["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer", "ner"])

print("Estrazione dei vettori in corso...")
# nlp.pipe processa tutto in un colpo solo, molto più velocemente
tokens = list(nlp.pipe(words))

# 3. Creazione della matrice e scrittura nel file
print("Inizio calcolo delle similarità. Questa operazione richiede un po' di tempo...")
total_words = len(tokens)

with open("word_vectors.csv", "w", encoding="utf-8") as f:
    f.write("word|vector\n")
    
    for i, token1 in enumerate(tokens):
        vector = []
        for token2 in tokens:
            if token1.has_vector and token2.has_vector:
                sim = round(token1.similarity(token2), 3)
                vector.append(sim)
            else:
                vector.append(0.0)
        
        f.write(f"{words[i]}|{vector}\n")
        
        # Stampa a schermo per mostrare il progresso ogni 100 parole
        if (i + 1) % 100 == 0:
            print(f"Completate {i + 1} parole su {total_words}...")

print("Finito! Il file word_vectors.csv è stato generato con successo.")