from typing import Annotated, Literal # <--- Importante
from bunnet import Document, Indexed
from lib.core.entities import TKBase, TKDictionary, TKName, TKPlace

_VECTOR_INDEX = "vector_index"

# Documento per le parole base
class TKBaseDoc(TKBase, Document):
    # Diciamo: "Il tipo è str, ed è indicizzato come unico"
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "base"

# Documento per il dizionario
class TKDictionaryDoc(TKDictionary, Document):
    word: Annotated[str, Indexed()]
    
    class Settings:
        name = "dictionary"

# Documento per i nomi propri
class TKNameDoc(TKName, Document):
    name: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "names"

# Documento per i luoghi
class TKPlaceDoc(TKPlace, Document):
    name: Annotated[str, Indexed()]

    class Settings:
        name = "places"