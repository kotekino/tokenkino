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

def bbox_to_geojson(bbox):
    """
    Converte [min_lat, max_lat, min_lon, max_lon] in un GeoJSON Polygon.
    """
    try:
        min_lat, max_lat, min_lon, max_lon = map(float, bbox)
        
        # Verifichiamo se il box è "serio" o solo un punto (es. > 0.001 gradi di lato)
        if abs(max_lat - min_lat) < 0.001 and abs(max_lon - min_lon) < 0.001:
            return None # Troppo piccolo per essere utile come contenitore
            
        return {
            "type": "Polygon",
            "coordinates": [[
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat] # Chiusura
            ]]
        }
    except Exception:
        return None

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
        
        # Saltiamo se già processato (Successo o Fallimento precedente)
        if registry.count_documents({"name": name, "type": f_type}, limit=1):
            print(f"⏭️ '{name}' ({f_type}) già presente nel registry, salto.")
            continue
        if skips.count_documents({"name": name, "type": f_type}, limit=1):
            print(f"⏭️ '{name}' ({f_type}) già segnato come skip, salto.")
            continue

        # Strategia di ricerca flessibile
        queries_to_try = [
            name,                                # Esempio: "pyrenees"
            f"{name} {f_type.replace('_', ' ')}" # Esempio: "pyrenees mountain range"
        ]
        
        found_polygon = False
        
        for q in queries_to_try:
            if found_polygon: break
            
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&polygon_geojson=1&addressdetails=1&limit=1"
            
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data:
                        item_data = data[0]
                        geom = item_data.get("geojson", {})
                        
                        # 1. Tentativo: Poligono Reale
                        if geom.get("type") in ["Polygon", "MultiPolygon"]:
                            final_geometry = geom
                            tqdm.write(f"✅ Poligono reale trovato per {name}")
                        
                        # 2. Fallback: Bounding Box (se il poligono manca o è un punto)
                        else:
                            bbox_geom = bbox_to_geojson(item_data.get("boundingbox", []))
                            if bbox_geom:
                                final_geometry = bbox_geom
                                tqdm.write(f"📦 Bounding Box usato come fallback per {name}")
                            else:
                                final_geometry = None
                                
                        if final_geometry:
                            tqdm.write(f"✅ TROVATO: '{name}' tramite query '{q}'")
                            
                            osm_cc = data[0].get("address", {}).get("country_code", "").upper()
                            final_cc = osm_cc if osm_cc else item["cc"]
                            parent_geo = country_map.get(final_cc, "earth")
                            
                            registry.update_one(
                                {"name": name, "type": f_type},
                                {"$set": {
                                    "parent_geo": parent_geo,
                                    "geometry": geom,
                                    "processed": False,
                                    "relevance_score": item["relevance"]
                                }},
                                upsert=True
                            )
                            found_polygon = True
                            success += 1
                
                # Rispetto rigoroso dei server Nominatim
                time.sleep(1.2)
                
            except Exception as e:
                tqdm.write(f"💥 Errore di rete su '{q}': {e}")
                time.sleep(5)
                continue

        # Se dopo tutti i tentativi non abbiamo trovato un poligono
        if not found_polygon:
            tqdm.write(f"❌ '{name}': Nessun poligono trovato dopo tutti i tentativi.")
            skips.update_one(
                {"name": name, "type": f_type},
                {"$set": {"reason": "no_polygon_found", "tried_queries": queries_to_try}},
                upsert=True
            )

    print(f"\n✅ Fine sessione. Nuovi poligoni nel registry: {success}")
    client.close()

if __name__ == "__main__":
    run_discovery()