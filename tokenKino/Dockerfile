FROM python:3.14-slim

WORKDIR /api

# copy only the files needed for installing dependencies first, to leverage Docker cache
COPY pyproject.toml .
# redundant but to be sure to have all the files needed for installing dependencies
COPY requirements.txt . 

# dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e .

RUN python -m spacy download en_core_web_md

# copy rest of code
COPY . .

#run fastapi
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]