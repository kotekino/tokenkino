from transformers import MarianMTModel, MarianTokenizer

class TKTranslator:
    def __init__(self):
        model_name = "Helsinki-NLP/opus-mt-mul-en"
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)

    def translate(self, text: str) -> str:
        batch = self.tokenizer([text], return_tensors="pt")
        generated_ids = self.model.generate(**batch)
        return self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]