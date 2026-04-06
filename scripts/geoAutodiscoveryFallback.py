import os
import requests
import pymongo
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_REGISTRY = "polygon_registry"
FILE_COUNTRIES = "./data/countryInfo.txt"

# Mappatura Continentale: Continent Code -> Landmass
LANDMASS_MAPPING = {
    "EU": "eurasia", "AS": "eurasia", 
    "AF": "africa_phys", 
    "NA": "americas", "SA": "americas", 
    "OC": "oceania_phys", "AN": "antarctica_phys"
}

OFFLINE_SEED = {
    "peninsula": [
        "Italian Peninsula", "Iberian Peninsula", "Balkan Peninsula", 
        "Scandinavian Peninsula", "Arabian Peninsula", "Kamchatka Peninsula",
        "Florida Peninsula", "Yucatan Peninsula", "Korean Peninsula"
    ],
    "mountain_range": [
        "Alps", "Apennines", "Andes", "Himalayas", "Rocky Mountains", 
        "Ural Mountains", "Caucasus Mountains", "Pyrenees", "Carpathian Mountains"
    ],
    "plain": [
        "Po Valley", "Great Plains", "North European Plain", "Indo-Gangetic Plain",
        "Pampas", "Amazon Basin"
    ],
    "island": [
        "Sicily", "Sardinia", "Corsica", "Great Britain", "Ireland", 
        "Honshu", "Madagascar", "Greenland", "Borneo"
    ],
    "desert": [
        "Sahara", "Gobi Desert", "Atacama Desert", "Kalahari Desert", 
        "Mojave Desert", "Arabian Desert"
    ]
}

# ==========================================
# 2. DICTIONARY BUILDER
# ==========================================
def build_country_to_landmass():
    mapping = {}
    if not os.path.exists(FILE_COUNTRIES):
        print(f"⚠️ Errore: {FILE_COUNTRIES} non trovato! Le entità andranno in 'earth'.")
        return mapping
        
    with open(FILE_COUNTRIES, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            parts = line.split('\t')
            iso_code = parts[0]      # Es: IT
            continent_code = parts[8] # Es: EU
            mapping[iso_code] = LANDMASS_MAPPING.get(continent_code, "earth")
    return mapping

# ==========================================
# 3. FALLBACK ENGINE
# ==========================================
def run_fallback_discovery():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    registry = db[COLLECTION_REGISTRY]
    
    # Costruiamo la mappa in RAM: {"IT": "eurasia", "US": "americas", ...}
    country_to_landmass = build_country_to_landmass()
    
    headers = {'User-Agent': 'SemanticGeoEngine/Fallback-2.0'}

    print("🚀 Avvio Fallback Discoverer V2 (Con Risoluzione Landmass Corretta)...")

    total_success = 0

    for feature_type, names in OFFLINE_SEED.items():
        print(f"\n{'='*40}\n📦 PROCESSANDO CATEGORIA: {feature_type.upper()}\n{'='*40}")
        
        for name in names:
            if registry.count_documents({"name": name.lower()}) > 0:
                print(f"  ⏩ '{name}' già nel DB. Salto.")
                continue
                
            print(f"  🔍 Cerco poligono per: {name}...")
            url = f"https://nominatim.openstreetmap.org/search?q={name}&format=json&polygon_geojson=1&addressdetails=1&limit=1"
            
            try:
                res = requests.get(url, headers=headers)
                if res.status_code == 200 and len(res.json()) > 0:
                    data = res.json()[0]
                    geom = data.get("geojson", {})
                    
                    if geom.get("type") in ["Polygon", "MultiPolygon"]:
                        
                        # Fix: Prendiamo il Country Code e lo diamo in pasto alla mappa generata da countryInfo.txt
                        country_code = data.get("address", {}).get("country_code", "").upper()
                        parent_geo = country_to_landmass.get(country_code, "earth")
                        
                        registry.insert_one({
                            "name": name.lower(),
                            "type": feature_type,
                            "parent_geo": parent_geo,
                            "geometry": geom,
                            "processed": False
                        })
                        print(f"    ✅ Poligono salvato! (Nazione Centroid: {country_code or 'N/D'} -> Landmass: {parent_geo.upper()})")
                        total_success += 1
                    else:
                        print(f"    ❌ OSM ha restituito un Punto, non un Poligono.")
                else:
                    print(f"    ❌ Non trovato su OSM con questo nome.")
                    
            except Exception as e:
                print(f"    ⚠️ Errore di connessione su '{name}': {e}")
            
            time.sleep(1.5) 
            
    print(f"\n🏁 FALLBACK COMPLETATO! {total_success} nuovi poligoni pronti nel Registry.")
    client.close()

if __name__ == "__main__":
    run_fallback_discovery()