from fastapi import APIRouter, Request

import src.schemas
from src.models import application

from src.db import database


router = APIRouter(
    prefix="/applications",
    tags=['Applications']
)


@router.post("/")
async def create(app: src.schemas.ApplicationIn):
    _app = await database.fetch_one(query=application.select().where(application.c.token == app.token))
    if _app is None:
        query = application.insert().values(
            token=app.token,
            name=app.name
        )
        record_id = await database.execute(query)
    else:
        record_id = _app.id
    return {"id": record_id}

