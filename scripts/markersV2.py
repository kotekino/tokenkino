import json

# Le 24 ancore base che abbiamo scelto
base_anchors = {
    "in", "on", "at", "from", "to", "over", "through", 
    "after", "while", "before", "until", "if", "since", 
    "although", "except", "of", "with", "like", "as", 
    "for", "and", "or", "but", "that"
}

# Leggiamo il JSON gigante che hai estratto
with open("./data/tokeniko.markers.json", "r", encoding="utf-8") as file:
    all_markers = json.load(file)

base_markers = []

# Filtriamo e ripuliamo i documenti
for doc in all_markers:
    if doc.get("word") in base_anchors:
        # Rimuoviamo i campi indesiderati (il secondo parametro 'None' evita errori se la chiave non esiste)
        doc.pop("_id", None)
        doc.pop("marker_type", None)
        
        base_markers.append(doc)

# Salviamo il nuovo JSON ridotto e pulito
with open("./data/tokeniko.markers.base.json", "w", encoding="utf-8") as file:
    json.dump(base_markers, file, indent=2)

print(f"Fatto! Salvati {len(base_markers)} marker base ripuliti nel nuovo file JSON.")