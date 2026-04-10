from fastapi import FastAPI
from lib.llc.functions import llc
from lib.tagger.functions import tagger

app = FastAPI()

@app.get("/process")
def read_root():
    res = llc() + " " + tagger()
    return {"status": "success", "data": res}