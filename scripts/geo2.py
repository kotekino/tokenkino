import os
import pymongo
from tqdm import tqdm

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_PLACES = "places"

FILE_COUNTRIES = "./data/countryInfo.txt"
FILE_REGIONS = "./data/admin1CodesASCII.txt"
FILE_CITIES = "./data/cities500.txt"
FILE_ALL_COUNTRIES = "./data/allCountries.txt"

COSMIC_BRIDGE = ["universe", "local group", "milky way", "solar system", "earth"]

LANDMASS_MAPPING = {
    "EU": "eurasia", "AS": "eurasia", 
    "AF": "africa_phys", 
    "NA": "americas", "SA": "americas", 
    "OC": "oceania_phys", "AN": "antarctica_phys"
}

POLITICAL_CONTINENTS = {
    "AF": "africa", "AS": "asia", "EU": "europe", 
    "NA": "north america", "SA": "south america", 
    "OC": "oceania", "AN": "antarctica"
}

TARGET_FEATURE_CLASSES = {
    "H": "hydrographic",
    "T": "terrestrial"
}

# ==========================================
# 2. IN-MEMORY DICTIONARIES
# ==========================================
countries_dict = {}  
regions_dict = {}    

def load_lookups():
    print("Loading Continents, Landmasses and Countries into RAM...")
    with open(FILE_COUNTRIES, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("#") or not line.strip(): continue
            parts = line.split('\t')
            iso_code = parts[0]
            country_name = parts[4].lower()
            continent_code = parts[8]
            
            continent_admin = POLITICAL_CONTINENTS.get(continent_code, "unknown")
            landmass_geo = LANDMASS_MAPPING.get(continent_code, "earth")
            
            countries_dict[iso_code] = {
                "name": country_name,
                "continent_admin": continent_admin,
                "landmass_geo": landmass_geo
            }

    print("Loading Regions into RAM...")
    with open(FILE_REGIONS, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            parts = line.split('\t')
            code = parts[0] 
            region_name = parts[2].lower()
            regions_dict[code] = region_name

# ==========================================
# 3. MAIN INGESTION
# ==========================================
def main():
    load_lookups()
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Opzionale: pulizia collection se non hai ri-fatto la init prima di questo script
    # db.drop_collection(COLLECTION_PLACES)
    
    collection = db[COLLECTION_PLACES]
    write_buffer = []
    BATCH_SIZE = 5000

    # ---------------------------------------------------------
    # STEP 1: Political Continents
    # ---------------------------------------------------------
    print("\n1. Building Political Continents...")
    for code, name in POLITICAL_CONTINENTS.items():
        landmass = LANDMASS_MAPPING.get(code, "earth")
        doc = {
            "name": name,
            "type": "continent",
            "category": "administrative",
            "parent_admin": "earth",
            "path_admin": [name],
            "parent_geo": landmass,
            "path_geo": COSMIC_BRIDGE + [landmass]
        }
        write_buffer.append(doc)

    collection.insert_many(write_buffer)
    write_buffer.clear()

    # ---------------------------------------------------------
    # STEP 2 & 3: Countries and Regions
    # ---------------------------------------------------------
    print("2. Building Countries and Regions...")
    
    # Countries
    for iso_code, info in countries_dict.items():
        doc = {
            "name": info["name"],
            "type": "country",
            "category": "administrative",
            "parent_admin": info["continent_admin"],
            "path_admin": [info["continent_admin"], info["name"]],
            "parent_geo": info["landmass_geo"],
            "path_geo": COSMIC_BRIDGE + [info["landmass_geo"]]
        }
        write_buffer.append(doc)
        
    # Regions
    for code, region_name in regions_dict.items():
        country_iso = code.split('.')[0]
        c_info = countries_dict.get(country_iso, {"name": "unknown", "continent_admin": "unknown", "landmass_geo": "earth"})
        
        doc = {
            "name": region_name,
            "type": "region",
            "category": "administrative",
            "parent_admin": c_info["name"],
            "path_admin": [c_info["continent_admin"], c_info["name"], region_name],
            "parent_geo": c_info["landmass_geo"],
            "path_geo": COSMIC_BRIDGE + [c_info["landmass_geo"]]
        }
        write_buffer.append(doc)

    collection.insert_many(write_buffer)
    write_buffer.clear()

    # ---------------------------------------------------------
    # STEP 4: Cities (The Admin-Geo Bridge + GPS Coordinates)
    # ---------------------------------------------------------
    print("3. Building Cities with GeoJSON points...")
    total_cities = sum(1 for _ in open(FILE_CITIES, 'r', encoding='utf-8'))
    with open(FILE_CITIES, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=total_cities, desc="Cities"):
            if not line.strip(): continue
            parts = line.split('\t')
            
            city_name = parts[2].lower()
            lat = float(parts[4]) if parts[4] else 0.0
            lon = float(parts[5]) if parts[5] else 0.0
            country_code = parts[8]
            admin1_code = parts[10]
            region_key = f"{country_code}.{admin1_code}"
            
            c_info = countries_dict.get(country_code, {"name": "unknown", "continent_admin": "unknown", "landmass_geo": "earth"})
            region_name = regions_dict.get(region_key)
            
            path_admin = [c_info["continent_admin"], c_info["name"]]
            parent_admin = c_info["name"]
            
            if region_name:
                path_admin.append(region_name)
                parent_admin = region_name
            
            path_admin.append(city_name)
            
            doc = {
                "name": city_name,
                "type": "city",
                "category": "administrative",
                "parent_admin": parent_admin,
                "path_admin": path_admin,
                "parent_geo": c_info["landmass_geo"],
                "path_geo": COSMIC_BRIDGE + [c_info["landmass_geo"]],
                "location": {
                    "type": "Point",
                    "coordinates": [lon, lat] # GeoJSON richiede [Longitudine, Latitudine]
                }
            }
            write_buffer.append(doc)
            
            if len(write_buffer) >= BATCH_SIZE:
                collection.insert_many(write_buffer, ordered=False)
                write_buffer.clear()
                
    if write_buffer: collection.insert_many(write_buffer, ordered=False); write_buffer.clear()

    # ---------------------------------------------------------
    # STEP 5: Natural Features (Pure Geo + GPS Coordinates)
    # ---------------------------------------------------------
    print("4. Building Natural Features with GeoJSON points...")
    total_features = sum(1 for _ in open(FILE_ALL_COUNTRIES, 'r', encoding='utf-8'))
    
    with open(FILE_ALL_COUNTRIES, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=total_features, desc="Geography"):
            if not line.strip(): continue
            parts = line.split('\t')
            
            feature_class = parts[6]
            if feature_class not in TARGET_FEATURE_CLASSES:
                continue
                
            name = parts[2].lower()
            try:
                lat = float(parts[4])
                lon = float(parts[5])
            except ValueError:
                continue # Salta se per qualche motivo mancano le coordinate
                
            country_code = parts[8]
            landmass = countries_dict.get(country_code, {}).get("landmass_geo", "earth")
            
            doc = {
                "name": name,
                "type": TARGET_FEATURE_CLASSES[feature_class],
                "category": "geographical",
                "parent_admin": "",
                "path_admin": [],
                "parent_geo": landmass,
                "path_geo": COSMIC_BRIDGE + [landmass, name],
                "location": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            }
            write_buffer.append(doc)
            
            if len(write_buffer) >= BATCH_SIZE:
                collection.insert_many(write_buffer, ordered=False)
                write_buffer.clear()

    if write_buffer: collection.insert_many(write_buffer, ordered=False)

    print("\n✅ Ingestion Totale Geospaziale Completata!")
    
    print("Creazione Indici in corso (potrebbe richiedere qualche secondo/minuto)...")
    collection.create_index([("name", pymongo.ASCENDING)])
    collection.create_index([("type", pymongo.ASCENDING)])
    collection.create_index([("path_admin", pymongo.ASCENDING)])
    collection.create_index([("path_geo", pymongo.ASCENDING)])
    # IL NUOVO INDICE MAGICO:
    collection.create_index([("location", pymongo.GEOSPHERE)])
    
    client.close()

if __name__ == "__main__":
    main()