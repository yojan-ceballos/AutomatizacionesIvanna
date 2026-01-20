from fastapi import FastAPI, Request
import os

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/oauth2/callback")
def oauth_callback(request: Request):
    code = request.query_params.get("code")
    return {
        "message": "Authorization code received",
        "code": code
    }
