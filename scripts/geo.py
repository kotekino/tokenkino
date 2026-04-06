import requests
import pymongo
import time

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_REGISTRY = "polygon_registry"

# Diciamo allo script cosa cercare e come categorizzarlo ontologicamente
TARGETS = [
    {
        "search_query": "Italian Peninsula",
        "name": "italian peninsula",
        "type": "peninsula",
        "parent_geo": "eurasia"
    },
    {
        "search_query": "Iberian Peninsula",
        "name": "iberian peninsula",
        "type": "peninsula",
        "parent_geo": "eurasia"
    }
]

def download_polygons():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    registry = db[COLLECTION_REGISTRY]

    # Nominatim richiede un User-Agent valido per non bloccare le richieste
    headers = {
        'User-Agent': 'SemanticGeoEngineBot/1.0 (tuo@indirizzo.email)'
    }

    print("🌐 Avvio del Downloader Geospaziale (Nominatim API)...")

    for target in TARGETS:
        query = target["search_query"]
        print(f"  🔍 Cerco i confini per: {query}...")

        # Chiamata API: chiediamo esplicitamente il polygon_geojson
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&polygon_geojson=1&limit=1"
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200 and len(response.json()) > 0:
            data = response.json()[0]
            
            if "geojson" in data:
                geometry = data["geojson"]
                
                # Nominatim a volte restituisce Punti se non ha il poligono esatto. Verifichiamo.
                if geometry["type"] not in ["Polygon", "MultiPolygon"]:
                    print(f"  ⚠️ Attenzione: Nominatim non ha un poligono per '{query}', ha restituito un {geometry['type']}. Salto.")
                    continue

                # Creiamo il documento per il nostro Registry
                registry_doc = {
                    "name": target["name"],
                    "type": target["type"],
                    "parent_geo": target["parent_geo"],
                    "geometry": geometry,
                    "processed": False  # Segnaliamo che è "da lavorare"
                }

                # Inseriamo o aggiorniamo (usando il nome come chiave univoca)
                registry.update_one(
                    {"name": target["name"]}, 
                    {"$set": registry_doc}, 
                    upsert=True
                )
                print(f"  ✅ Poligono di '{target['name']}' salvato nel Registry (In attesa di elaborazione).")
            else:
                print(f"  ❌ Nessun GeoJSON trovato per '{query}'.")
        else:
            print(f"  ❌ Errore API o nessun risultato per '{query}'.")
            
        time.sleep(1.5) # Rispetto dei limiti di rate delle API pubbliche

    print("\n🏁 Download completato. Il Registry è aggiornato.")
    client.close()

if __name__ == "__main__":
    download_polygons()