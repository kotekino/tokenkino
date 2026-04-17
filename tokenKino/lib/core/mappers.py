from typing import Optional

class TKPosMapper:
    """
    Utility class per mappare i POS tag tra spaCy (Universal Dependencies) 
    e WordNet (usato in TKDictionary).
    """
    
    # Molti-a-Uno: Da spaCy a WordNet
    _SPACY_TO_WN = {
        "NOUN": "n",
        "VERB": "v",
        "AUX": "v",
        "ADJ": "a",    # spaCy non fa distinzione tra 'a' e 's'
        "ADV": "r"
    }

    # Uno-a-Default: Da WordNet al default di spaCy (per generazione/ricostruzione)
    _WN_TO_SPACY_DEFAULT = {
        "n": "NOUN",
        "v": "VERB",
        "a": "ADJ",
        "s": "ADJ",    # I satellite diventano ADJ standard
        "r": "ADV"
    }

    @classmethod
    def get_wn_pos(cls, spacy_pos: str) -> Optional[str]:
        """
        Dato un tag POS di spaCy (es. 'AUX'), restituisce l'equivalente WordNet (es. 'v').
        Restituisce None se è una particella non supportata da WordNet (es. 'ADP').
        """
        return cls._SPACY_TO_WN.get(spacy_pos.upper())

    @classmethod
    def get_spacy_default(cls, wn_pos: str) -> Optional[str]:
        """
        Dato un tag POS di WordNet (es. 's'), restituisce il default spaCy (es. 'ADJ').
        """
        return cls._WN_TO_SPACY_DEFAULT.get(wn_pos.lower())