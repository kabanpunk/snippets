from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware

from src.routers import notes, videos, users, applications
from src.db import database, create_all

create_all()

from src.models import direction, video, user_action, user_recommendation
from src.db import engine

app = FastAPI()
origins = [
    "http://localhost:8080",
    "http://37.192.52.216:8080",
    "http://0.0.0.0:8080",
    "http://localhost",
    "http://37.192.52.216",
    "http://0.0.0.0",
    
]

app.include_router(videos.router)
app.include_router(users.router)
app.include_router(applications.router)

app.mount("/static", StaticFiles(directory="src/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    allow_headers=["Access-Control-Allow-Headers", 'Content-Type', 'Authorization', 'Access-Control-Allow-Origin', "Set-Cookie", "X-PINGOTHER"],
)

templates = Jinja2Templates(directory="src/templates")


@app.on_event("startup")
async def startup():
    await database.connect()

    dirs = {
        "up": 0,
        "down": 0,
        "left": -1,
        "right": 1,
    }

    user_action.drop(engine)
    user_recommendation.drop(engine)
    video.drop(engine)
    direction.drop(engine)

    create_all() 

    for key, value in dirs.items():
        await database.execute(direction.insert().values(
            name=key,
            ratio=value
        ))



@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/items/")
def read_root(request: Request):
    client_host = request.client.host
    return {"client_host": client_host}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, token: str, platform: str, lat: float, lon: float):
    from models import user
    _user = await database.fetch_one(query=user.select().where(user.c.token == token))

    if _user is None:
        query = user.insert().values(token=token, platform=platform, geo={"lat": lat, "lon": lon})
        user_id = await database.execute(query)
    else:
        user_id = _user.id

    return templates.TemplateResponse(
        "index.html", {
            "request": request,
            "user_id": user_id,
            "token": token,
            "platform": platform,
            "lat": lat,
            "lon": lon
        }
    )
