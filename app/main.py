from fastapi import FastAPI

from app.routers.categories import router as categories_router
from app.routers.trends import router as trends_router

app = FastAPI(title="yt-insight-lab")

app.include_router(categories_router)
app.include_router(trends_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
