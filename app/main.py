from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine, Base
from app.routers.categories import router as categories_router
from app.routers.videos import router as videos_router
from app.routers.trends import router as trends_router
from app.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="yt-insight-lab", lifespan=lifespan)

app.include_router(categories_router)
app.include_router(videos_router)
app.include_router(trends_router)


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
