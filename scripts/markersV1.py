import urllib.request
import pymongo
import spacy_stanza
import nltk
from nltk.corpus import wordnet

# --- INIZIO PATCH PYTORCH ---
import torch

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# ==========================================
# FASE 0: PREPARAZIONE
# ==========================================
print("--- FASE 0: Preparazione risorse ---")
# Scarica il dizionario WordNet in modo silenzioso (se già presente, viene ignorato)
nltk.download('wordnet', quiet=True)

# Connessione a MongoDB
MONGO_URI = "mongodb://localhost:27018/?directConnection=true"
client = pymongo.MongoClient(MONGO_URI)
db = client['tokeniko']
collection = db['markers']
print("Connessione a MongoDB stabilita.")

# Caricamento del modello NLP
print("Caricamento della pipeline spacy-stanza (potrebbe richiedere un momento)...")
nlp = spacy_stanza.load_pipeline(
    "en",
    device="mps",                       # silicon gpu acceleration (if available)
    download_method="reuse_resources"   # skip download if already present
)

# ==========================================
# FASE 1: DOWNLOAD E ANALISI DATI CoNLL-U
# ==========================================
print("\n--- FASE 1: Estrazione dati dal Treebank UD ---")
url = "https://raw.githubusercontent.com/UniversalDependencies/UD_English-EWT/master/en_ewt-ud-train.conllu"

print("Scaricamento del dataset in corso...")
response = urllib.request.urlopen(url)
conllu_data = response.read().decode('utf-8')

all_function_words = set()

# Estrazione delle particelle
for line in conllu_data.split('\n'):
    line = line.strip()
    if not line or line.startswith('#'):
        continue
        
    fields = line.split('\t')
    if len(fields) == 10:
        word = fields[1].lower()
        deprel_base = fields[7].split(':')[0]
        
        # Uniamo sia 'case' che 'mark' nello stesso set
        if deprel_base in ["case", "mark"]:
            all_function_words.add(word)

print(f"Estrazione completata! Trovate {len(all_function_words)} particelle uniche.")

# ==========================================
# FASE 2: FUNZIONI DI SUPPORTO
# ==========================================
# ==========================================
# FASE 2: FUNZIONI DI SUPPORTO (AGGIORNATA)
# ==========================================
def get_definition(word):
    """
    Cerca la definizione su WordNet limitando la ricerca agli Avverbi ('r').
    WordNet non supporta preposizioni/congiunzioni, quindi l'avverbio
    è l'approssimazione semantica più vicina per le function words.
    Restituisce una stringa vuota se non c'è corrispondenza utile.
    """
    # Cerchiamo solo synset catalogati come avverbi (ADV)
    synsets_adv = wordnet.synsets(word, pos=wordnet.ADV)
    
    if synsets_adv:
        # Restituiamo la definizione del primo avverbio trovato
        return synsets_adv[0].definition()
    
    # Modifica 2: Nessuna definizione pertinente trovata -> stringa vuota
    return ""

# ==========================================
# FASE 3: ELABORAZIONE E SALVATAGGIO (MONGO)
# ==========================================
print("\n--- FASE 3: Generazione vettori e salvataggio su DB ---")
print("Elaborazione in corso, per favore attendi...")

count_inserimenti = 0

for word in all_function_words:
    # 1. Estrazione del vettore semantico con spacy-stanza
    doc = nlp(word)
    vector = doc[0].vector.tolist() if len(doc) > 0 else []
    
    # 2. Estrazione della definizione
    definition = get_definition(word)
    
    # 3. Creazione del documento per MongoDB
    document = {
        "word": word,
        "vector": vector,
        "definition": definition
    }
    
    # 4. Salvataggio su DB (Upsert previene duplicati se rilanci lo script)
    collection.update_one(
        {"word": word},
        {"$set": document},
        upsert=True
    )
    count_inserimenti += 1
    
    # Stampa un piccolo log di progresso ogni 50 parole elaborate
    if count_inserimenti % 50 == 0:
        print(f"Elaborate e salvate {count_inserimenti}/{len(all_function_words)} parole...")

print(f"\nPipeline completata con successo! Tutti i {count_inserimenti} record sono stati elaborati e salvati in MongoDB ('tokeniko' -> 'function_words').")