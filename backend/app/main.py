from fastapi import FastAPI

app = FastAPI(title="AI Settlement Exception Resolver")


@app.get("/")
def root():
    return {
        "message": "AI Settlement Exception Resolver API"
    }


@app.get("/settlements")
def get_settlements():
    return {
        "settlements": [
            {
                "id": "SET001",
                "amount": 10000,
                "status": "matched"
            },
            {
                "id": "SET002",
                "amount": 7500,
                "status": "exception"
            }
        ]
    }