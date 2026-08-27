from fastapi import FastAPI

from app.api.tax_api import router as tax_router


app = FastAPI(title="TaxLens AI - Tax Line Matcher")


app.include_router(tax_router)


@app.get("/")
def root():
    return {
        "message": "TaxLens AI is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }