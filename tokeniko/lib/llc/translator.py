import logging
import os

from huggingface_hub import constants as hf_constants, snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError
from transformers import MarianMTModel, MarianTokenizer

_MODEL_NAME = "Helsinki-NLP/opus-mt-mul-en"


# scarica i pesi del modello disabilitando temporaneamente la modalita' offline
# di HuggingFace (HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE), poi ripristina lo stato
# precedente. usato solo come fallback quando la cache locale e' assente.
def _download_offline_bypass(model_name: str) -> None:
    prev_env = {k: os.environ.get(k) for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    prev_const = hf_constants.HF_HUB_OFFLINE

    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"
    # is_offline_mode() legge questa costante a runtime: va forzata, non basta l'env
    hf_constants.HF_HUB_OFFLINE = False
    try:
        snapshot_download(model_name)
    finally:
        hf_constants.HF_HUB_OFFLINE = prev_const
        for k, v in prev_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# garantisce che il modello sia in cache locale. se manca (prima installazione o
# cache persa), lo recupera silenziosamente scaricandolo una volta: cosi' il load
# offline successivo non fallisce con il fuorviante "source spm None" (TypeError).
def _ensure_model_cached(model_name: str) -> None:
    try:
        snapshot_download(model_name, local_files_only=True)
        return
    except (LocalEntryNotFoundError, OSError):
        pass

    logging.warning("MarianMT model %s not in local cache; downloading once...", model_name)
    _download_offline_bypass(model_name)


class TKTranslator:
    def __init__(self):
        model_name = _MODEL_NAME
        _ensure_model_cached(model_name)
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)

    def translate(self, text: str) -> str:
        batch = self.tokenizer([text], return_tensors="pt")
        generated_ids = self.model.generate(**batch)
        return self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
