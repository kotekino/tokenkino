from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from lib.llc.functions import llc
from lib.tagger.functions import tagger
from dotenv import load_dotenv
from lib.core.io import init_io

# env load (MONGO_URI, ecc.)
load_dotenv()

# define lifespan for startup and shutdown logic
async def lifespan(app: FastAPI):

    # IO init
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME", "tokenkino")    
    client = init_io(connection_string=uri, db_name=db_name)
    
    yield  #where fastapi runs
    
    # shutdown logic
    client.close()

# init fastapi app
app = FastAPI(lifespan=lifespan)

# endpoints
@app.get("/process")
def read_root():
    res = llc() + " " + tagger()
    return {"status": "success", "data": res}