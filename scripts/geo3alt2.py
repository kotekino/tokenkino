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
FILE_COUNTRIES_INFO = "./data/countryInfo.txt"

LANDMASS_MAPPING = {
    "EU": "eurasia", "AS": "eurasia", "AF": "africa_phys",
    "NA": "americas", "SA": "americas", "OC": "oceania_phys", "AN": "antarctica_phys"
}

# ==========================================
# 2. THE CURATED MASTERLIST
# ==========================================
CURATED_FEATURES = {
    "peninsula": [
        "Iberian Peninsula", "Italian Peninsula", "Balkan Peninsula", "Scandinavian Peninsula", 
        "Arabian Peninsula", "Kamchatka Peninsula", "Florida Peninsula", "Yucatan Peninsula", 
        "Korean Peninsula", "Indochina Peninsula", "Horn of Africa", "Crimean Peninsula",
        "Peloponnese", "Anatolian Peninsula", "Sinai Peninsula"
    ],
    "mountain_range": [
        "Alps", "Apennines", "Andes", "Himalayas", "Rocky Mountains", "Ural Mountains", 
        "Caucasus Mountains", "Pyrenees", "Carpathian Mountains", "Atlas Mountains", 
        "Appalachian Mountains", "Zagros Mountains", "Tien Shan", "Hindu Kush", 
        "Karakoram", "Sierra Nevada", "Cascades"
    ],
    "plain": [
        "Po Valley", "Great Plains", "North European Plain", "Indo-Gangetic Plain", 
        "Pampas", "Nullarbor Plain", "Siberian Plain", "Mesopotamian Marshes"
    ],
    "drainage_basin": [
        "Amazon Basin", "Congo Basin", "Mississippi Basin", "Murray-Darling Basin", 
        "Lake Chad Basin", "Tarim Basin"
    ],
    "island": [
        "Sicily", "Sardinia", "Corsica", "Great Britain", "Ireland", 
        "Honshu", "Hokkaido", "Kyushu", "Shikoku", 
        "Madagascar", "Greenland", "Borneo", "Sumatra", "Java", "New Guinea", 
        "Baffin Island", "Victoria Island", "Cuba", "Hispaniola", "Iceland", 
        "Sri Lanka", "Tasmania", "Taiwan"
    ],
    "archipelago": [
        "Japanese Archipelago", "British Isles", "Philippine Archipelago", 
        "Malay Archipelago", "Canary Islands", "Balearic Islands", 
        "Hawaiian Islands", "Galapagos Islands", "Azores", "Falkland Islands"
    ],
    "desert": [
        "Sahara", "Gobi Desert", "Atacama Desert", "Kalahari Desert", 
        "Mojave Desert", "Arabian Desert", "Patagonian Desert", 
        "Great Victoria Desert", "Syrian Desert", "Taklamakan Desert", "Sonoran Desert"
    ],
    "plateau": [
        "Tibetan Plateau", "Colorado Plateau", "Deccan Plateau", "Anatolian Plateau",
        "Iranian Plateau", "Altiplano"
    ]
}

# ==========================================
# 3. UTILS & ENGINE
# ==========================================
def get_country_to_landmass():
    mapping = {}
    if not os.path.exists(FILE_COUNTRIES_INFO):
        print(f"⚠️ {FILE_COUNTRIES_INFO} non trovato! Le landmass di default saranno 'earth'.")
        return mapping
    with open(FILE_COUNTRIES_INFO, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            parts = line.split('\t')
            mapping[parts[0].strip().upper()] = LANDMASS_MAPPING.get(parts[8].strip().upper(), "earth")
    return mapping

def run_curated_discovery():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Pulizia totale del registry: partiamo da zero con la lista curata
    db[COLLECTION_REGISTRY].delete_many({})
    registry = db[COLLECTION_REGISTRY]
    
    country_map = get_country_to_landmass()
    headers = {'User-Agent': 'SemanticGeoEngine/Curated-Discovery-1.0'}

    # Appiattiamo il dizionario in una lista di task
    tasks = []
    for f_type, names in CURATED_FEATURES.items():
        for name in names:
            tasks.append({"name": name.lower(), "type": f_type})

    print(f"🌟 Inizio Discovery Curato: {len(tasks)} feature geografiche di classe mondiale.")
    
    success_count = 0
    fail_count = 0

    for item in tqdm(tasks, desc="Scaricamento Poligoni"):
        name = item["name"]
        f_type = item["type"]
        
        queries_to_try = [
            name, 
            f"{name} {f_type.replace('_', ' ')}"
        ]
        
        found = False
        
        for q in queries_to_try:
            if found: break
            
            url = f"https://nominatim.openstreetmap.org/search?q={q}&format=json&polygon_geojson=1&addressdetails=1&limit=1"
            
            try:
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data and "geojson" in data[0]:
                        geom = data[0]["geojson"]
                        
                        # ACCETTIAMO SOLO POLIGONI VERI
                        if geom["type"] in ["Polygon", "MultiPolygon"]:
                            osm_cc = data[0].get("address", {}).get("country_code", "").upper()
                            parent_geo = country_map.get(osm_cc, "earth")
                            
                            registry.insert_one({
                                "name": name,
                                "type": f_type,
                                "parent_geo": parent_geo,
                                "geometry": geom,
                                "processed": False,
                                "source": "curated_masterlist"
                            })
                            found = True
                            success_count += 1
                            tqdm.write(f"✅ {name.title()} ({f_type}): Poligono perfetto trovato.")
                
                time.sleep(1.2)
                
            except Exception as e:
                tqdm.write(f"💥 Errore di rete su '{q}': {e}")
                time.sleep(5)

        if not found:
            tqdm.write(f"❌ {name.title()}: Nessun poligono reale trovato. Verrà ignorato.")
            fail_count += 1

    print(f"\n🏁 Fine. Poligoni incamerati: {success_count} | Falliti: {fail_count}")
    client.close()

if __name__ == "__main__":
    run_curated_discovery()