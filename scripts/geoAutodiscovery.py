import requests
import pymongo
import time
from SPARQLWrapper import SPARQLWrapper, JSON

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:64820/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_REGISTRY = "polygon_registry"

MACRO_CLASSES = {
    "drainage_basin": "wd:Q81389",
    "mountain_range": "wd:Q46831",
    "plain": "wd:Q160736",
    "plateau": "wd:Q107046",
    "peninsula": "wd:Q34724",
    "desert": "wd:Q8514",
    "valley": "wd:Q1314",
    "island": "wd:Q23442",
    "archipelago": "wd:Q33837",
    "sea": "wd:Q165"
}

# La nostra fidata mappa mentale: Codice Nazione (OSM) -> Massa Fisica
LANDMASS_MAPPING = {
    "EU": "eurasia", "AS": "eurasia", 
    "AF": "africa_phys", 
    "NA": "americas", "SA": "americas", 
    "OC": "oceania_phys", "AN": "antarctica_phys"
}

LIMIT_PER_QUERY = 150 # Estraiamo le top 150 mondiali per ogni categoria

# ==========================================
# 2. DISCOVERY ENGINE V3 (LOGIC SHIFT)
# ==========================================
def run_v3_discovery():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    registry = db[COLLECTION_REGISTRY]
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    
    headers = {'User-Agent': 'SemanticGeoEngine/3.0'}

    print("🚀 Avvio Scout V3: Wikidata (Classifica Globale) + Nominatim (Risoluzione Geografica)...")

    for feature_type, feature_wd in MACRO_CLASSES.items():
        print(f"\n{'='*50}\n🔍 ESTRAZIONE CLASSIFICA MONDIALE: {feature_type.upper()}\n{'='*50}")
        
        # Query senza ORDER BY, usa la presenza su Wiki EN come garanzia di importanza
        query = f"""
        SELECT DISTINCT ?itemLabel WHERE {{
          ?item wdt:P31 {feature_wd} .
          
          # TRUCCO: Esige che esista un articolo sulla Wikipedia in inglese
          ?article schema:about ?item ;
                   schema:isPartOf <https://en.wikipedia.org/> .
                   
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT {LIMIT_PER_QUERY}
        """
        
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        
        try:
            results = sparql.query().convert()
        except Exception as e:
            print(f"  ❌ Errore Wikidata per {feature_type}: {e}")
            time.sleep(5) # Pausa più lunga in caso di server momentaneamente down
            continue

        # Nota: avendo rimosso ?sitelinks, estraiamo solo l'etichetta
        discovered = [r["itemLabel"]["value"].lower() for r in results["results"]["bindings"]]
        discovered = list(set([n for n in discovered if not n.startswith("q")]))
        
        print(f"  🎯 Wikidata ha risposto in un lampo: trovati i {len(discovered)} top '{feature_type}' mondiali.")
        
        success_count = 0
        
        for name in discovered:
            if registry.count_documents({"name": name}) > 0:
                print(f"    ⏩ '{name}' già nel DB. Salto.")
                continue
                
            # Aggiunto addressdetails=1 per farci restituire il country_code da Nominatim
            url = f"https://nominatim.openstreetmap.org/search?q={name}&format=json&polygon_geojson=1&addressdetails=1&limit=1"
            
            try:
                res = requests.get(url, headers=headers)
                if res.status_code == 200 and len(res.json()) > 0:
                    data = res.json()[0]
                    geom = data.get("geojson", {})
                    
                    if geom.get("type") in ["Polygon", "MultiPolygon"]:
                        
                        # LOGICA DI MAPPATURA CONTINENTALE IN PYTHON!
                        address = data.get("address", {})
                        country_code = address.get("country_code", "").upper()
                        
                        # Risolviamo la landmass. Se non ha country (es. Oceani), finisce in "earth"
                        parent_geo = LANDMASS_MAPPING.get(country_code, "earth")
                        
                        registry.insert_one({
                            "name": name,
                            "type": feature_type,
                            "parent_geo": parent_geo,
                            "geometry": geom,
                            "processed": False
                        })
                        print(f"    ✅ '{name}' -> Trovato in {country_code or 'Acque Int.'} -> Assegnato a '{parent_geo.upper()}'.")
                        success_count += 1
                    else:
                        print(f"    ❌ '{name}' -> Nominatim ha solo un Punto, non un Poligono.")
                else:
                    print(f"    ❌ '{name}' -> Non trovato su OpenStreetMap.")
                    
            except Exception as e:
                print(f"    ⚠️ Errore di rete su '{name}'.")
            
            time.sleep(1.2) # Pausa di cortesia per Nominatim
            
        print(f"  🏁 Categoria '{feature_type}' completata! Acquisiti {success_count} poligoni validi.")

    print("\n✅ DISCOVERY V3 TERMINATA! Nessun server è stato maltrattato.")
    client.close()

if __name__ == "__main__":
    run_v3_discovery()