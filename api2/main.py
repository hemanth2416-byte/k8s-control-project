from fastapi import FastAPI
import socket

app = FastAPI()

@app.get("/api2/health")
def health():
    return {"status": "ok", "service": "api2", "host": socket.gethostname()}

@app.get("/api2/hello")
def hello():
    return {"message": "Hello from API2"}
