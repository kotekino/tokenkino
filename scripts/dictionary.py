import os
import re
import numpy as np
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
import concurrent.futures
from tqdm import tqdm

# Download NLTK data quietly
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)
nltk.download('stopwords', quiet=True)

stop_words = set(stopwords.words('english'))

# 1. Configuration
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
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
def calculate_glossary(word):
    """Calculates the glossary token set for a single word."""
    synsets = wn.synsets(word)
    tokens = set()
    for syn in synsets:
        phrase = syn.definition()
        for ex in syn.examples(): phrase += " " + ex
        clean_words = re.findall(r'\b[a-z]+\b', phrase.lower())
        for p in clean_words:
            if p not in stop_words and len(p) > 2:
                tokens.add(p)
    return tokens

def get_primary_meanings(word):
    """Extracts ONLY the primary meaning for each Part of Speech."""
    all_synsets = wn.synsets(word)
    filtered_synsets = []
    seen_pos = set()
    for s in all_synsets:
        if s.pos() not in seen_pos:
            filtered_synsets.append(s)
            seen_pos.add(s.pos())
    return filtered_synsets

def get_semantic_value(target_word, base_word, target_gloss, base_gloss):
    if target_word == base_word:
        return 1.0
        
    s1 = wn.synsets(target_word)
    s2 = wn.synsets(base_word)
    
    if not s1 or not s2: return 0.0

    set1 = set(s1)
    set2 = set(s2)
    
    # A. Explicit Synonyms
    if set1.intersection(set2): return 1.0

    # B. Antonyms
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for ant in lemma.antonyms():
                if ant.synset() in set2: return -1.0
                        
    # C. Morphological Derivations
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for drf in lemma.derivationally_related_forms():
                if drf.synset() in set2: return 0.9

    # D. Hierarchical Similarity (Filtered)
    max_sim = 0.0
    s1_primary = get_primary_meanings(target_word)
    s2_primary = get_primary_meanings(base_word)
    
    for ss1 in s1_primary:
        for ss2 in s2_primary:
            if ss1.pos() == ss2.pos():
                sim = ss1.wup_similarity(ss2)
                if sim and sim > max_sim:
                    max_sim = sim
                
    if max_sim > 0.65:
        return round(max_sim, 3)
        
    # E. Gloss Overlap
    if target_gloss and base_gloss:
        overlap_count = len(target_gloss.intersection(base_gloss))
        if overlap_count >= 2:
            jaccard = overlap_count / len(target_gloss.union(base_gloss))
            score_overlap = min(round(jaccard * 5, 3), 0.5)
            if score_overlap > 0.1: return score_overlap
                
    return 0.0

# ==========================================
# FUNZIONE DI INIZIALIZZAZIONE DEL WORKER
# ==========================================
def init_worker():
    """
    Questa funzione viene eseguita UNA SOLA VOLTA da ogni Core (processo figlio) 
    appena viene "spawnato". Carica gli assi semantici nella memoria RAM isolata del core.
    """
    global BASE_WORDS_ORDERED, BASE_VECTORS_DICT, GLOSSARY_DICT_BASE
    
    # Ogni worker si fa la sua connessioncina al db per leggere le basi
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll_base = db[COLLECTION_BASE]
    
    base_docs = list(coll_base.find().sort("index", 1))
    
    for doc in base_docs:
        word = doc["word"]
        BASE_WORDS_ORDERED.append(word)
        BASE_VECTORS_DICT[word] = doc["vector"]
        GLOSSARY_DICT_BASE[word] = calculate_glossary(word)
        
    client.close() # Chiudiamo la connessione, il worker ora ha tutto in RAM!

# ==========================================
# MULTIPROCESSING WORKER
# ==========================================
def worker_process_word(target_word):
    # Ora i worker VEDRANNO questi dizionari pieni!
    if target_word in BASE_VECTORS_DICT:
        return target_word, BASE_VECTORS_DICT[target_word]

    vector = []
    target_gloss = calculate_glossary(target_word)
    
    for base_word in BASE_WORDS_ORDERED:
        val = get_semantic_value(target_word, base_word, target_gloss, GLOSSARY_DICT_BASE[base_word])
        vector.append(val)
        
    return target_word, vector

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
    with open(DICTIONARY_FILE, 'r', encoding='utf-8') as f:
        all_words = [line.strip().lower() for line in f if line.strip()]
    
    all_words = list(dict.fromkeys(all_words))

    # Resume Logic
    print("Checking database for resume logic...")
    already_processed = set(doc["word"] for doc in coll_dict.find({}, {"word": 1}))
    words_to_process = [p for p in all_words if p not in already_processed]

    print(f"Total words in txt: {len(all_words)}")
    print(f"Words already in DB: {len(already_processed)}")
    print(f"Words remaining: {len(words_to_process)}")

    if not words_to_process:
        print("All words have been processed. Exiting.")
        return

    max_workers = max(1, os.cpu_count() - 1)
    print(f"\nStarting distributed computation across {max_workers} cores...")
    # max_workers = 1  # <--- Forza a 1 core per ora, rimuovi questa linea per usare tutti i core disponibili

    write_buffer = []
    BATCH_SIZE = 500  

    # LA MAGIA È QUI: aggiungiamo initializer=init_worker
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
        results = executor.map(worker_process_word, words_to_process, chunksize=50)
        
        for target_word, vector in tqdm(results, total=len(words_to_process), desc="Computing Vectors"):
            write_buffer.append({
                "word": target_word,
                "vector": vector
            })

            if len(write_buffer) >= BATCH_SIZE:
                coll_dict.insert_many(write_buffer)
                write_buffer.clear()

    if write_buffer:
        coll_dict.insert_many(write_buffer)

    print("\n✅ Giant dictionary ingestion successfully completed!")
    client.close()

if __name__ == "__main__":
    main()