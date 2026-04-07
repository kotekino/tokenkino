import pymongo
import geopandas as gpd
import pandas as pd
from shapely.geometry import mapping
from tqdm import tqdm
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:49326/?directConnection=true"
DB_NAME = "semantic_engine"
COLLECTION_REGISTRY = "polygon_registry"

# Percorso in cui hai estratto lo zip di Natural Earth
SHAPEFILE_PATH = "./data/natural_earth/ne_10m_geography_regions_polys.shp"

# I nomi che Nominatim NON ha trovato
MISSING_TARGETS = {
    "scandinavian peninsula": ("peninsula", "eurasia"),
    "florida peninsula": ("peninsula", "americas"),
    "indochina peninsula": ("peninsula", "eurasia"),
    "horn of africa": ("peninsula", "africa_phys"),
    "anatolian peninsula": ("peninsula", "eurasia"),
    
    "andes": ("mountain_range", "americas"),
    "rocky mountains": ("mountain_range", "americas"),
    "ural mountains": ("mountain_range", "eurasia"),
    "caucasus mountains": ("mountain_range", "eurasia"),
    "atlas mountains": ("mountain_range", "africa_phys"),
    "appalachian mountains": ("mountain_range", "americas"),
    "zagros mountains": ("mountain_range", "eurasia"),
    "tien shan": ("mountain_range", "eurasia"),
    "hindu kush": ("mountain_range", "eurasia"),
    "sierra nevada": ("mountain_range", "americas"),
    
    "great plains": ("plain", "americas"),
    "north european plain": ("plain", "eurasia"),
    "indo-gangetic plain": ("plain", "eurasia"),
    "nullarbor plain": ("plain", "oceania_phys"),
    "mesopotamian marshes": ("plain", "eurasia"),
    
    "congo basin": ("drainage_basin", "africa_phys"),
    "mississippi basin": ("drainage_basin", "americas"),
    "murray-darling basin": ("drainage_basin", "oceania_phys"),
    "lake chad basin": ("drainage_basin", "africa_phys"),
    "tarim basin": ("drainage_basin", "eurasia"),
    
    "japanese archipelago": ("archipelago", "eurasia"),
    "british isles": ("archipelago", "eurasia"),
    "philippine archipelago": ("archipelago", "eurasia"),
    "malay archipelago": ("archipelago", "eurasia"),
    
    "sahara": ("desert", "africa_phys"),
    "gobi desert": ("desert", "eurasia"),
    "atacama desert": ("desert", "americas"),
    "kalahari desert": ("desert", "africa_phys"),
    "arabian desert": ("desert", "eurasia"),
    "patagonian desert": ("desert", "americas"),
    "great victoria desert": ("desert", "oceania_phys"),
    "syrian desert": ("desert", "eurasia"),
    "sonoran desert": ("desert", "americas"),
    
    "tibetan plateau": ("plateau", "eurasia"),
    "colorado plateau": ("plateau", "americas"),
    "deccan plateau": ("plateau", "eurasia"),
    "anatolian plateau": ("plateau", "eurasia"),
    "iranian plateau": ("plateau", "eurasia")
}

def run_natural_earth_ingest():
    if not os.path.exists(SHAPEFILE_PATH):
        print(f"🛑 Errore: File {SHAPEFILE_PATH} non trovato.")
        return

    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    registry = db[COLLECTION_REGISTRY]

    print("🗺️  Caricamento dataset Natural Earth...")
    gdf = gpd.read_file(SHAPEFILE_PATH)
    
    # -----------------------------------------------------
    # FIX: Trova la colonna del nome in modo dinamico e sicuro
    # -----------------------------------------------------
    col_name = None
    # Cerchiamo prima i nomi più comuni negli shapefile
    for candidate in ['name', 'NAME', 'name_en', 'NAME_EN']:
        if candidate in gdf.columns:
            col_name = candidate
            break
            
    # Fallback: cerca qualsiasi colonna che contenga 'name'
    if not col_name:
        name_cols = [c for c in gdf.columns if 'name' in c.lower()]
        if name_cols:
            col_name = name_cols[0]
        else:
            print(f"🛑 Errore critico: Nessuna colonna nome trovata. Colonne presenti:\n{list(gdf.columns)}")
            return
            
    print(f"📌 Uso la colonna '{col_name}' per identificare le feature.")
    # -----------------------------------------------------

    success_count = 0
    print("🔍 Ricerca entità mancanti nel dataset...")

    for index, row in tqdm(gdf.iterrows(), total=len(gdf)):
        val = row[col_name]
        
        # Saltiamo le righe dove il nome è nullo (NaN)
        if pd.isna(val):
            continue
            
        feature_name_raw = str(val).lower().strip()
        
        matched_target = None
        for target in MISSING_TARGETS.keys():
            if target in feature_name_raw or feature_name_raw in target:
                matched_target = target
                break
                
        if matched_target:
            f_type, parent_geo = MISSING_TARGETS[matched_target]
            
            if registry.count_documents({"name": matched_target}) == 0:
                geom_geojson = mapping(row['geometry'])
                
                if geom_geojson['type'] in ['Polygon', 'MultiPolygon']:
                    registry.insert_one({
                        "name": matched_target,
                        "type": f_type,
                        "parent_geo": parent_geo,
                        "geometry": geom_geojson,
                        "processed": False,
                        "source": "natural_earth"
                    })
                    success_count += 1
                    tqdm.write(f"✅ Trovato e convertito: {matched_target.title()} (NE name: '{val}')")

    print(f"\n🏁 Fine. Poligoni recuperati da Natural Earth: {success_count} / {len(MISSING_TARGETS)}")
    client.close()

if __name__ == "__main__":
    run_natural_earth_ingest()