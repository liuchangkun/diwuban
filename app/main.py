from fastapi import FastAPI

from app.api.v1.router import api_v1_router

app = FastAPI(title="Pump Station Optimization API")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_v1_router, prefix="/api/v1")
