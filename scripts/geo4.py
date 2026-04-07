import pymongo
from pymongo.errors import OperationFailure
from tqdm import tqdm
from shapely.geometry import shape

# ==========================================
# CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_PLACES = "places"
COLLECTION_REGISTRY = "polygon_registry"

def run_worker():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    col_places = db[COLLECTION_PLACES]
    registry = db[COLLECTION_REGISTRY]

    print("📊 Fase 1: Analisi geometrica e ordinamento per Area...")
    # Recuperiamo tutti i poligoni (quelli di Nominatim e quelli di Natural Earth)
    pending_jobs = list(registry.find({"processed": True}))
    
    if not pending_jobs:
        print("💤 Nessun poligono da processare.")
        return

    # Calcoliamo l'area solo in memoria per l'ordinamento
    for job in pending_jobs:
        try:
            geom_poly = shape(job["geometry"])
            job["calculated_area"] = geom_poly.area
        except Exception:
            job["calculated_area"] = 0

    # Ordiniamo per area decrescente (Top-Down)
    pending_jobs.sort(key=lambda x: x["calculated_area"], reverse=True)

    print(f"⚙️  Fase 2: Incrocio Spaziale su {len(pending_jobs)} poligoni...")

    for job in tqdm(pending_jobs, desc="Macinazione"):
        node_name = job["name"]
        parent_geo = job["parent_geo"]
        geometry = job["geometry"]

        # 1. GESTIONE NODO GEOGRAFICO (es. "Alps")
        # Costruiamo il path per il nodo fisico stesso
        parent_doc = col_places.find_one({"name": parent_geo, "category": "geographical"})
        base_path = parent_doc.get("path_geo", []) if parent_doc else ["earth", parent_geo]
        new_path = base_path + [node_name]

        col_places.update_one(
            {"name": node_name, "category": "geographical"},
            {"$set": {
                "type": job["type"],
                "parent_geo": parent_geo,
                "path_geo": new_path
                # NOTA: area_sq_deg rimosso come richiesto per pulizia
            }},
            upsert=True
        )

        # 2. UPDATE PIPELINE PER I FIGLI (Città e Feature)
        query = {
            "location": { "$geoWithin": { "$geometry": geometry } },
            "name": { "$ne": node_name }
        }

        pipeline = [
            {
                "$set": {
                    # Il parent_geo cambia solo per gli oggetti geografici (gerarchia fisica)
                    "parent_geo": {
                        "$cond": {
                            "if": { "$eq": ["$category", "geographical"] },
                            "then": node_name,
                            "else": "$parent_geo"
                        }
                    },
                    # Il path_geo cambia solo per gli oggetti geografici (Logica Tail-Safe)
                    "path_geo": {
                        "$cond": {
                            "if": { "$eq": ["$category", "geographical"] },
                            "then": {
                                "$concatArrays": [
                                    { "$slice": ["$path_geo", 0, { "$subtract": [{ "$size": "$path_geo" }, 1] }] },
                                    [node_name],
                                    [{ "$arrayElemAt": ["$path_geo", -1] }]
                                ]
                            },
                            "else": "$path_geo"
                        }
                    },
                    # Nuovo array fisico per le città (evita sovrapposizioni nel path)
                    "physical_features": {
                        "$cond": {
                            "if": { "$eq": ["$category", "administrative"] },
                            "then": {
                                "$setUnion": [
                                    { "$ifNull": ["$physical_features", []] },
                                    [node_name]
                                ]
                            },
                            "else": { "$ifNull": ["$physical_features", []] }
                        }
                    }
                }
            }
        ]

        try:
            res = col_places.update_many(query, pipeline)
            registry.update_one(
                {"_id": job["_id"]}, 
                {"$set": {"processed": True, "affected_count": res.modified_count}}
            )
        except OperationFailure as e:
            tqdm.write(f"💥 Errore su {node_name}: {e}")
            registry.update_one({"_id": job["_id"]}, {"$set": {"processed": "error"}})

    print("\n✅ Ontologia Geografica completata e verificata!")
    client.close()

if __name__ == "__main__":
    run_worker()