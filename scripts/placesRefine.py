import pymongo
from pymongo.errors import OperationFailure
from tqdm import tqdm

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_PLACES = "places"
COLLECTION_REGISTRY = "polygon_registry"

# ==========================================
# 2. WORKER ENGINE
# ==========================================
def run_worker():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_places = db[COLLECTION_PLACES]
    registry = db[COLLECTION_REGISTRY]

    # peschiamo solo i lavori non ancora processati
    pending_jobs = list(registry.find({"processed": False}))
    
    if not pending_jobs:
        print("💤 Nessun nuovo poligono da processare nel Registry. Il Macinatore riposa.")
        client.close()
        return

    print(f"⚙️ Trovati {len(pending_jobs)} poligoni in coda. Avvio dell'Incrocio Geospaziale...\n")

    # Usiamo tqdm per avere una progress bar complessiva
    for job in tqdm(pending_jobs, desc="Macinando Poligoni"):
        node_name = job["name"]
        parent_name = job["parent_geo"]
        geometry = job["geometry"]

        # 1. Recupero dell'albero del genitore (la Landmass)
        parent_doc = col_places.find_one({"name": parent_name})
        if not parent_doc:
            # Se manca l'eurasia (impossibile se hai fatto l'init, ma siamo prudenti)
            registry.update_one({"_id": job["_id"]}, {"$set": {"processed": "error_missing_parent"}})
            continue
            
        base_path = parent_doc.get("path_geo", [])
        new_path = base_path + [node_name]

        # 2. Creazione/Aggiornamento del Nodo Fisico nell'albero
        col_places.update_one(
            {"name": node_name},
            {
                "$set": {
                    "type": job["type"],
                    "category": "geographical",
                    "parent_geo": parent_name,
                    "path_geo": new_path,
                    "path_admin": [] 
                }
            },
            upsert=True
        )

        # 3. Intersezione Geospaziale Massiva (Con gestione errori per poligoni complessi)
        query = {
            "location": {
                "$geoWithin": {
                    "$geometry": geometry
                }
            },
            # Idempotenza: non inseriamo due volte la stessa città nello stesso poligono
            "path_geo": { "$ne": node_name } 
        }

        update = {
            "$set": { "parent_geo": node_name },
            "$push": { "path_geo": node_name }
        }

        try:
            # Eseguiamo l'update su tutta la collection places
            result = col_places.update_many(query, update)
            
            # Segniamo il job come completato con successo
            registry.update_one(
                {"_id": job["_id"]}, 
                {
                    "$set": {
                        "processed": True, 
                        "matched_places": result.modified_count # Teniamo traccia di quante città ha "mangiato"
                    }
                }
            )
            
        except OperationFailure as e:
            # Catturiamo gli errori geometrici di MongoDB (es. Loop Intersection)
            registry.update_one(
                {"_id": job["_id"]}, 
                {
                    "$set": {
                        "processed": "geometry_error",
                        "error_details": str(e)
                    }
                }
            )

    print("\n🏁 Tutti i lavori in coda sono stati eseguiti!")
    print("Vai su Compass e controlla il `path_geo` delle tue città per ammirare la nuova granularità fisica.")
    client.close()

if __name__ == "__main__":
    run_worker()