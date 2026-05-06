from transformers import MarianMTModel, MarianTokenizer

# translator class via marian tokenizer
class TKTranslator:
    def __init__(self):
        # Carica pesi e tokenizzatore in RAM all'avvio del container
        model_name = "Helsinki-NLP/opus-mt-mul-en"
        print("Loadng NMT ...")
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)
        print("NMT ready")

    def translate(self, text: str) -> str:
        # 1. Trasforma il testo in tensori Pytorch
        batch = self.tokenizer([text], return_tensors="pt")
        
        # 2. Genera gli ID della traduzione (è totalmente deterministico)
        generated_ids = self.model.generate(**batch)
        
        # 3. Decodifica gli ID in una stringa inglese pulita
        translation = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return translation