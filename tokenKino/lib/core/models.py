from typing import Annotated, Literal # <--- Importante
from bunnet import Document, Indexed
from lib.core.entities import TKBase, TKDictionary, TKName, TKPlace

# Documento per le parole base
class BaseDoc(TKBase, Document):
    # Diciamo: "Il tipo è str, ed è indicizzato come unico"
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "tk_bases"

# Documento per il dizionario
class DictionaryDoc(TKDictionary, Document):
    word: Annotated[str, Indexed()]
    
    class Settings:
        name = "tk_dictionary"

# Documento per i nomi propri
class NameDoc(TKName, Document):
    name: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "tk_names"

# Documento per i luoghi
class PlaceDoc(TKPlace, Document):
    name: Annotated[str, Indexed()]

    class Settings:
        name = "tk_places"
        indexes = [
            [("location", "2dsphere")] 
        ]