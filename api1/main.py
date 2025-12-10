from fastapi import FastAPI
import socket

app = FastAPI()

@app.get("/api1/health")
def health():
    return {"status": "ok", "service": "api1", "host": socket.gethostname()}

@app.get("/api1/hello")
def hello():
    return {"message": "Hello from API1"}
