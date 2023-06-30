from typing import List

from fastapi import APIRouter, Request\

import src.schemas
from src.models import notes

from src.db import database

import json

router = APIRouter(
    prefix="/notes",
    tags=['Notes']
)


@router.get("/", response_model=List[src.schemas.Note])
async def read_notes():
    query = notes.select()
    return await database.fetch_all(query)


@router.post("/")
async def create_note(request: Request):
    _note = await database.fetch_one(query=notes.select().where(notes.c.ip == request.client.host))
    if _note is None:
        query = notes.insert().values(ip=request.client.host, data={})
        record_id = await database.execute(query)
    else:
        record_id = _note.id
    return {"id": record_id}


@router.post("/{video_name}")
async def choice(video_name: str, option: bool,  request: Request):
    _note = notes.select().where(notes.c.ip == request.client.host)
    _data = json.loads((await database.fetch_one(query=_note)).data)

    if video_name in _data:
        _data[video_name] += 1 if option else -1
    else:
        _data[video_name] = 1 if option else -1

    query = notes.update().where(notes.c.ip == request.client.host).values(data=_data)
    await database.execute(query)
    return 'success'
