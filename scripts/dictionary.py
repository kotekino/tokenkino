from operator import pos
import os
import re
import numpy as np
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
import concurrent.futures
from tqdm import tqdm
from nltk.stem import WordNetLemmatizer

# Download NLTK data quietly
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('stopwords', quiet=True)
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_BASE = "base"  # Must match the output collection of the previous script
COLLECTION_DICT = "dictionary"
DICTIONARY_FILE = "data/dictionary.txt" # <--- Provide your 350k word file here

# Global variables for Workers (Loaded into RAM for all cores)
BASE_WORDS_ORDERED = []
BASE_VECTORS_DICT = {}
GLOSSARY_DICT_BASE = {}

# ==========================================
# SEMANTIC FUNCTIONS
# ==========================================
def calculate_synset_glossary(syn):
    """Calcola la gloss overlap SOLO per uno specifico significato (Synset)."""
    phrase = syn.definition()
    for ex in syn.examples(): 
        phrase += " " + ex
    clean_words = re.findall(r'\b[a-z]+\b', phrase.lower())
    tokens = set()
    for p in clean_words:
        if p not in stop_words and len(p) > 2:
            tokens.add(p)
    return tokens

def calculate_base_glossary(word):
    """Calcola la gloss overlap globale per la parola BASE (come ancora semantica)."""
    synsets = wn.synsets(word)
    tokens = set()
    for syn in synsets:
        phrase = syn.definition()
        for ex in syn.examples(): 
            phrase += " " + ex
        clean_words = re.findall(r'\b[a-z]+\b', phrase.lower())
        for p in clean_words:
            if p not in stop_words and len(p) > 2:
                tokens.add(p)
    return tokens

def get_primary_meanings(word, max_per_pos=3):
    """
    Estrae fino a 'max_per_pos' significati per ogni Part of Speech.
    Include fallback di lemmatizzazione a cascata per le forme flesse.
    """
    all_synsets = wn.synsets(word)
    
    if not all_synsets:
        for pos_tag in ['v', 'n', 'a', 'r']:
            lemma = lemmatizer.lemmatize(word, pos=pos_tag)
            if lemma != word:
                all_synsets = wn.synsets(lemma)
                if all_synsets:
                    break

    filtered_synsets = []
    
    # Inizializziamo i contatori per Nomi, Verbi, Aggettivi (a/s) e Avverbi
    pos_counts = {'n': 0, 'v': 0, 'a': 0, 's': 0, 'r': 0}
    
    for s in all_synsets:
        pos = s.pos()
        # Se non abbiamo ancora raggiunto il limite (es. 3) per questo POS, lo aggiungiamo
        if pos_counts.get(pos, 0) < max_per_pos:
            filtered_synsets.append(s)
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
            
    return filtered_synsets

def get_semantic_value(target_word, target_synset, base_word, target_gloss, base_gloss):
    """Calcola la vicinanza semantica tra un Synset specifico e una parola Base."""
    if target_word == base_word:
        return 1.0
        
    s2 = wn.synsets(base_word)
    if not s2: 
        return 0.0

    set2 = set(s2)
    
    # A. Explicit Synonyms
    if target_synset in set2: 
        return 1.0

    # B. Antonyms (Basato solo sui lemmi di questo specifico synset)
    for lemma in target_synset.lemmas():
        for ant in lemma.antonyms():
            if ant.synset() in set2: 
                return -1.0
                        
    # C. Morphological Derivations
    for lemma in target_synset.lemmas():
        for drf in lemma.derivationally_related_forms():
            if drf.synset() in set2: 
                return 0.9

    # D. Hierarchical Similarity (Filtered)
    max_sim = 0.0
    s2_primary = get_primary_meanings(base_word)
    
    for ss2 in s2_primary:
        if target_synset.pos() == ss2.pos():
            sim = target_synset.wup_similarity(ss2)
            if sim and sim > max_sim:
                max_sim = sim
                
    if max_sim > 0.65:
        return round(max_sim, 3)
        
    # E. Gloss Overlap (Gloss specifica del synset target vs gloss generica base)
    if target_gloss and base_gloss:
        overlap_count = len(target_gloss.intersection(base_gloss))
        if overlap_count >= 2:
            jaccard = overlap_count / len(target_gloss.union(base_gloss))
            score_overlap = min(round(jaccard * 5, 3), 0.5)
            if score_overlap > 0.1: 
                return score_overlap
                
    return 0.0

# ==========================================
# WORKER INITIALIZATION
# ==========================================
def init_worker():
    """Inizializza la RAM del singolo core con le ancore di base."""
    global BASE_WORDS_ORDERED, BASE_VECTORS_DICT, GLOSSARY_DICT_BASE
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll_base = db[COLLECTION_BASE]
    
    base_docs = list(coll_base.find().sort("index", 1))
    
    for doc in base_docs:
        word = doc["word"]
        BASE_WORDS_ORDERED.append(word)
        BASE_VECTORS_DICT[word] = doc["vector"]
        GLOSSARY_DICT_BASE[word] = calculate_base_glossary(word)
        
    client.close()

# ==========================================
# MULTIPROCESSING WORKER
# ==========================================
def worker_process_word(target_word):
    """Elabora una parola restituendo una lista di significati e relativi vettori."""
    results = []
    primary_synsets = get_primary_meanings(target_word)
    
    # CASO 1: Parola non presente in WordNet (es. slang, nomi propri)
    if not primary_synsets:
        return results

    # CASO 2: Calcoliamo il vettore per ogni significato primario (pos)
    for syn in primary_synsets:
        vector = []
        target_gloss = calculate_synset_glossary(syn)
        
        for base_word in BASE_WORDS_ORDERED:
            val = get_semantic_value(target_word, syn, base_word, target_gloss, GLOSSARY_DICT_BASE[base_word])
            vector.append(val)
            
        results.append({
            "word": target_word,
            "pos": syn.pos(),                     # 'n', 'v', 'a', 'r'
            "sense": syn.name(),                  # es. 'bank.n.01'
            "definition": syn.definition(),       # Salviamo la definizione per debug
            "vector": vector
        })
        
    return results

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    print("Initializing Main Process...")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll_dict = db[COLLECTION_DICT]

    # Legge il file TXT
    print("Reading dictionary file...")
    if not os.path.exists(DICTIONARY_FILE):
        print(f"🛑 Error: Dictionary file not found at {DICTIONARY_FILE}")
        return

    with open(DICTIONARY_FILE, 'r', encoding='utf-8') as f:
        all_words = [line.strip().lower() for line in f if line.strip()]
    
    # Rimuoviamo duplicati dal file txt
    all_words = list(dict.fromkeys(all_words))

    # Resume Logic (uso di distinct per non saturare la RAM con centinaia di migliaia di object)
    print("Checking database for resume logic...")
    already_processed = set(coll_dict.distinct("word"))
    words_to_process = [p for p in all_words if p not in already_processed]

    print(f"Total words in txt: {len(all_words)}")
    print(f"Words already in DB: {len(already_processed)}")
    print(f"Words remaining: {len(words_to_process)}")

    if not words_to_process:
        print("All words have been processed. Exiting.")
        return

    max_workers = max(1, os.cpu_count() - 1)
    print(f"\nStarting distributed computation across {max_workers} cores...")

    write_buffer = []
    BATCH_SIZE = 1000  # Aumentato il batch size dato che usiamo extend

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
        results = executor.map(worker_process_word, words_to_process, chunksize=50)
        
        for list_of_meanings in tqdm(results, total=len(words_to_process), desc="Computing Vectors"):
            write_buffer.extend(list_of_meanings)

            if len(write_buffer) >= BATCH_SIZE:
                coll_dict.insert_many(write_buffer)
                write_buffer.clear()

    # Inserimento rimanenze
    if write_buffer:
        coll_dict.insert_many(write_buffer)

    print("\n✅ Giant dictionary ingestion successfully completed!")
    
    # Suggerimento per le performance: creare un indice sul campo "word" per future letture veloci
    print("Creating index on 'word' field for faster lookups...")
    coll_dict.create_index("word")
    
    client.close()

if __name__ == "__main__":
    main()