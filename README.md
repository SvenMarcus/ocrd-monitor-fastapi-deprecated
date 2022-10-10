# Experimental OCRD Monitor with FastAPI

## Installation

Install with 
```
pip3 install -r requirements.txt
```

## Running

Before starting the server, launch an instance of the OCRD Browser on `localhost:8085`.

Then start the server with 
```bash
uvicorn ocrdbrowser_server.main:app --reload
```