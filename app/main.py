from fastapi import FastAPI

app = FastAPI(title="Lyftr AI Backend")

@app.get("/")
async def root():
    return {"message": "Lyftr AI Backend is running"}
