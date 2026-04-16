from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Query
from pymongo import MongoClient
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
    db_name = os.getenv("MONGO_DB_NAME")    
    db_client = init_io(connection_string=uri, db_name=db_name)
    app.state.db_client = db_client
    
    yield  #where fastapi runs
    
    # shutdown logic
    db_client.close()

# init fastapi app
app = FastAPI(lifespan=lifespan)

# endpoints
@app.get("/process")
def read_root(q: str = Query(..., min_length=3, description="Sentence to submit")):
    res = llc(q, app.state.db_client)
    return {"status": "success", "data": res}

