import PyPDF2
import re
import numpy as np
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords

# Download NLTK data (only runs if not already downloaded)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

# English stop words to filter out meaningless words in definitions
stop_words = set(stopwords.words('english'))

# Global dictionary to hold pre-calculated word definitions (glossaries) in memory
GLOSSARY_DICT = {}

# 1. MongoDB Configuration
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_NAME = "base"

# 2. Extract words from the PDF (Oxford 3000)
def extract_words():
    words = []
    print("Extracting words from PDF...")
    with open('data/The_Oxford_3000.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                line = line.strip()
                if not line: continue
                
                # Match words formatted like "abandon A2"
                m = re.match(r'^([a-zA-Z-]+)\s+.*[A-C][1-2]$', line)
                if m:
                    words.append(m.group(1).lower())
                else:
                    # Fallback for differently formatted lines
                    parts = line.split()
                    if len(parts) >= 3 and parts[-1] in ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']:
                        word = re.sub(r'[^a-z-]', '', parts[0].lower())
                        if word: words.append(word)
                        
    # Return a deduplicated list while preserving order
    return list(dict.fromkeys(words))

# 3. Filter for primary meanings
def get_primary_meanings(word):
    """
    Extracts ONLY the primary meaning for each Part of Speech (Noun, Verb, Adjective).
    This prevents false positives caused by rare, obsolete, or slang definitions.
    """
    all_synsets = wn.synsets(word)
    filtered_synsets = []
    seen_pos = set()
    
    for s in all_synsets:
        # Keep the first (most common) synset for each POS
        if s.pos() not in seen_pos:
            filtered_synsets.append(s)
            seen_pos.add(s.pos())
            
    return filtered_synsets

# 4. Advanced Semantic Engine
def get_semantic_value(target_word, base_word):
    # Identity
    if target_word == base_word:
        return 1.0
        
    s1 = wn.synsets(target_word)
    s2 = wn.synsets(base_word)
    
    if not s1 or not s2: 
        return 0.0

    set1 = set(s1)
    set2 = set(s2)

    # ==============================================================
    # A. EXPLICIT SYNONYMS
    # ==============================================================
    # If they share at least one Synset, they are synonyms (Score: 1.0)
    if set1.intersection(set2):
        return 1.0

    # ==============================================================
    # B. ANTONYMS (Score: -1.0)
    # ==============================================================
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for ant in lemma.antonyms():
                if ant.synset() in set2:
                    return -1.0
                        
    # ==============================================================
    # C. MORPHOLOGICAL DERIVATIONS (e.g., able -> ability)
    # ==============================================================
    for syn1 in s1:
        for lemma in syn1.lemmas():
            for drf in lemma.derivationally_related_forms():
                if drf.synset() in set2:
                    return 0.9  # Very strong correlation
                    
    # ==============================================================
    # D. HIERARCHICAL SIMILARITY (WU-PALMER) - FILTERED
    # ==============================================================
    max_sim = 0.0
    
    # Use only primary meanings to avoid slang/rare definitions
    s1_primary = get_primary_meanings(target_word)
    s2_primary = get_primary_meanings(base_word)
    
    for ss1 in s1_primary:
        for ss2 in s2_primary:
            # Only compare within the same POS (Noun-Noun, Verb-Verb)
            if ss1.pos() == ss2.pos():
                sim = ss1.wup_similarity(ss2)
                if sim and sim > max_sim:
                    max_sim = sim
                
    # Strict threshold to avoid deep-tree false positives
    if max_sim > 0.65:
        return round(max_sim, 3)
    
    # ==============================================================
    # E. GLOSS OVERLAP (Domain Correlation)
    # ==============================================================
    gloss1 = GLOSSARY_DICT.get(target_word, set())
    gloss2 = GLOSSARY_DICT.get(base_word, set())
    
    if gloss1 and gloss2:
        intersection = gloss1.intersection(gloss2)
        overlap_count = len(intersection)
        
        # If they share at least 2 meaningful words in their definitions
        if overlap_count >= 2:
            # Calculate Jaccard Index (Intersection / Union)
            jaccard = overlap_count / len(gloss1.union(gloss2))
            
            # Amplify the score but cap it at 0.5 (below strict hierarchy)
            score_overlap = min(round(jaccard * 5, 3), 0.5)
            
            # Discard microscopic noise
            if score_overlap > 0.1:
                return score_overlap    
        
    return 0.0

# 5. Pre-calculate glossaries (definitions) into memory
def precalculate_glossaries(words):
    print("Pre-calculating glossaries (definitions) in memory...")
    for word in words:
        synsets = wn.synsets(word)
        tokens = set()
        for syn in synsets:
            # Get definition
            phrase = syn.definition()
            # Append examples
            for ex in syn.examples():
                phrase += " " + ex
            
            # Clean string: lowercase, letters only
            clean_words = re.findall(r'\b[a-z]+\b', phrase.lower())
            for p in clean_words:
                # Discard stop words and short fragments
                if p not in stop_words and len(p) > 2:
                    tokens.add(p)
                    
        GLOSSARY_DICT[word] = tokens
    print("Glossaries loaded successfully!")

# 6. Main process with incremental saving
def main():
    words = extract_words()
    total = len(words)
    
    # Load definitions into RAM
    precalculate_glossaries(words)
    
    print(f"Starting analysis on {total} base words for collection '{COLLECTION_NAME}'...")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    for i, target in enumerate(words):
        print(f"Calculating vector for: '{target}' ({i + 1}/{total})...")
        
        # RESUME LOGIC: Check if word is already processed
        if collection.find_one({"word": target}):
            print(f"  -> Skipping '{target}' (already in DB)")
            continue

        vector = []
        for base in words:
            val = get_semantic_value(target, base)
            vector.append(val)
        
        # Immediate insert to MongoDB
        collection.insert_one({
            "word": target,
            "vector": vector,
            "index": i # Keeps track of original axis order
        })

    print(f"\n✅ Operation complete! {COLLECTION_NAME} is ready.")
    client.close()
    
if __name__ == "__main__":
    main()