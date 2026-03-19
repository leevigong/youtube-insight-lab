from fastapi import FastAPI

from app.routers.categories import router as categories_router

app = FastAPI(title="yt-insight-lab")

app.include_router(categories_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
