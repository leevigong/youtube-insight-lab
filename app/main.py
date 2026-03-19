from fastapi import FastAPI

app = FastAPI(title="yt-insight-lab")


@app.get("/")
def root():
    return {"message": "yt-insight-lab"}
