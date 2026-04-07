import os
import requests
import pymongo
import time
from tqdm import tqdm

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_REGISTRY = "polygon_registry"
COLLECTION_SKIPS = "discovery_skips" 
FILE_ALL_COUNTRIES = "./data/allCountries.txt"
FILE_COUNTRIES_INFO = "./data/countryInfo.txt"

# Soglia di importanza: (n. nomi alternativi). 
# Alzala (es. 12-15) per avere solo i "pesi massimi" mondiali.
IMPORTANCE_THRESHOLD = 10 

TARGET_CODES = {
    "PEN": "peninsula", "MTS": "mountain_range", "PLN": "plain",
    "DSRT": "desert", "ISL": "island", "ISLS": "archipelago",
    "BSN": "drainage_basin", "PLAT": "plateau", "VAL": "valley"
}

LANDMASS_MAPPING = {
    "EU": "eurasia", "AS": "eurasia", "AF": "africa_phys",
    "NA": "americas", "SA": "americas", "OC": "oceania_phys", "AN": "antarctica_phys"
}

# ==========================================
# 2. UTILS
# ==========================================
def get_country_to_landmass():
    mapping = {}
    if not os.path.exists(FILE_COUNTRIES_INFO):
        print(f"⚠️ Attenzione: {FILE_COUNTRIES_INFO} non trovato!")
        return mapping
    with open(FILE_COUNTRIES_INFO, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            parts = line.split('\t')
            mapping[parts[0].strip().upper()] = LANDMASS_MAPPING.get(parts[8].strip().upper(), "earth")
    return mapping

# ==========================================
# 3. DISCOVERY ENGINE
# ==========================================
def run_discovery():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    registry = db[COLLECTION_REGISTRY]
    skips = db[COLLECTION_SKIPS]
    
    country_map = get_country_to_landmass()
    headers = {'User-Agent': 'SemanticGeoEngine/Mass-Discovery-3.0'}

    # --- FASE 1: ESTRAZIONE E FILTRO ---
    print(f"⛏️  Fase 1: Scansione locale con soglia rilevanza {IMPORTANCE_THRESHOLD}...")
    raw_features = []
    
    with open(FILE_ALL_COUNTRIES, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.split('\t')
            if len(parts) < 10: continue
            
            f_code = parts[7]
            if f_code in TARGET_CODES:
                # Calcolo rilevanza basato sui nomi alternativi (Colonna 4)
                alt_names = parts[3].split(',') if parts[3] else []
                relevance = len(alt_names)
                
                if relevance >= IMPORTANCE_THRESHOLD:
                    raw_features.append({
                        "name": parts[2].lower(),
                        "type": TARGET_CODES[f_code],
                        "cc": parts[8].strip().upper(),
                        "relevance": relevance
                    })

    # Ordiniamo e rimuoviamo duplicati
    raw_features.sort(key=lambda x: x['relevance'], reverse=True)
    unique_features = {}
    for f in raw_features:
        key = (f["name"], f["type"])
        if key not in unique_features:
            unique_features[key] = f
            
    final_list = list(unique_features.values())

    print(f"🎯 Selezione completata: {len(final_list)} entità di alta rilevanza.")
    print(f"🌐 Fase 2: Interrogazione Nominatim (Strategia Doppio Tentativo)...")
    
    # --- FASE 2: INTERROGAZIONE ---
    success = 0

    for item in tqdm(final_list):
        name = item["name"]
        f_type = item["type"]
  
        # appende item in un file di testo
        with open("test_output.txt", "a") as f:
            f.write(f"{name}: {f_type}\n")

if __name__ == "__main__":
    run_discovery()