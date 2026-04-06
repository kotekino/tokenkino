import pymongo

MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_PLACES = "places"

def initialize_geo_base():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # 💥 Rasiamo al suolo la collection per ripartire puliti
    db.drop_collection(COLLECTION_PLACES)
    collection = db[COLLECTION_PLACES]

    # --- 1. ASTRONOMICAL ENTITIES ---
    cosmos = [
        {"name": "universe", "type": "root", "category": "geographical", "parent_admin": "", "parent_geo": "", "path_admin": [], "path_geo": ["universe"]},
        {"name": "local group", "type": "galaxy_cluster", "category": "geographical", "parent_admin": "", "parent_geo": "universe", "path_admin": [], "path_geo": ["universe", "local group"]},
        {"name": "milky way", "type": "galaxy", "category": "geographical", "parent_admin": "", "parent_geo": "local group", "path_admin": [], "path_geo": ["universe", "local group", "milky way"]},
        {"name": "solar system", "type": "star_system", "category": "geographical", "parent_admin": "", "parent_geo": "milky way", "path_admin": [], "path_geo": ["universe", "local group", "milky way", "solar system"]},
        {"name": "earth", "type": "planet", "category": "geographical", "parent_admin": "", "parent_geo": "solar system", "path_admin": [], "path_geo": ["universe", "local group", "milky way", "solar system", "earth"]}
    ]

    # --- 2. GLOBAL PHYSICAL ENTITIES (5 Oceans & Landmasses) ---
    earth_path = ["universe", "local group", "milky way", "solar system", "earth"]
    
    physical_base = [
        # I 5 Oceani della Terra
        {"name": "atlantic ocean", "type": "ocean", "parent_geo": "earth", "path_geo": earth_path + ["atlantic ocean"]},
        {"name": "pacific ocean", "type": "ocean", "parent_geo": "earth", "path_geo": earth_path + ["pacific ocean"]},
        {"name": "indian ocean", "type": "ocean", "parent_geo": "earth", "path_geo": earth_path + ["indian ocean"]},
        {"name": "arctic ocean", "type": "ocean", "parent_geo": "earth", "path_geo": earth_path + ["arctic ocean"]},
        {"name": "southern ocean", "type": "ocean", "parent_geo": "earth", "path_geo": earth_path + ["southern ocean"]},
        
        # Masse terrestri (I continenti fisici separati da quelli politici)
        {"name": "eurasia", "type": "landmass", "parent_geo": "earth", "path_geo": earth_path + ["eurasia"]},
        {"name": "africa_phys", "type": "landmass", "parent_geo": "earth", "path_geo": earth_path + ["africa_phys"]},
        {"name": "americas", "type": "landmass", "parent_geo": "earth", "path_geo": earth_path + ["americas"]},
        {"name": "oceania_phys", "type": "landmass", "parent_geo": "earth", "path_geo": earth_path + ["oceania_phys"]},
        {"name": "antarctica_phys", "type": "landmass", "parent_geo": "earth", "path_geo": earth_path + ["antarctica_phys"]}
    ]

    # Uniformiamo lo schema per le entità fisiche
    for entry in physical_base:
        entry["category"] = "geographical"
        entry["parent_admin"] = ""
        entry["path_admin"] = []
        
    # Inserimento massivo
    collection.insert_many(cosmos + physical_base)

    print("✅ Collection azzerata e Inizializzazione Cosmica/Fisica completata (con 5 oceani)!")
    client.close()

if __name__ == "__main__":
    initialize_geo_base()