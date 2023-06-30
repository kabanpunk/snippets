import string
import os
import random
from typing import List

from fastapi import APIRouter, Request
from fastapi import FastAPI, UploadFile, File, HTTPException

import src.schemas
from src.models import video, user_recommendation, user

from src.db import database

router = APIRouter(
    prefix="/videos",
    tags=['Videos']
)


@router.get("/list", response_model=List[src.schemas.Video])
async def get_list():
    query = video.select()
    return await database.fetch_all(query=query)


@router.get("/random-list", response_model=List[src.schemas.Video])
async def get_random_list():
    query = video.select()
    videos = await database.fetch_all(query=query)
    random.shuffle(videos)
    return videos


@router.delete("/", status_code=200)
async def remove(video_name: str):
    query = video.delete().where(video.c.name == video_name)
    return await database.execute(query)


@router.post("/upload/multiple")
async def multiple_upload(files: List[UploadFile]):
    videos_names = []
    for file in files:
        videos_names.append(await upload_(file))
    return videos_names


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_name = await upload_(file)
    return {"video_name": video_name}


async def upload_(file: UploadFile) -> str:
    video_name = gen_name(32)  # ''.join(file.filename.split('.')[:-1])

    contents = file.file.read()
    if file.filename.split('.')[-1] != 'mp4':
        file.file.close()
        raise HTTPException(status_code=422, detail="The file format must be MP4 only")
    if file.filename.count('.') > 1:
        file.file.close()
        raise HTTPException(status_code=422, detail="Incorrect file name")

    video_path = os.getcwd() + '/src/static/' + video_name + '.mp4'

    file.file.close()
    with open(video_path, 'wb') as f:
        f.write(contents)

    video_id = await database.execute(
        query=video.insert().values(
            name=video_name
        )
    )

    _users = await database.fetch_all(
        query=user.select()
    )
    for _user in _users:
        await database.execute(
            query=user_recommendation.insert().values(
                video_id=video_id,
                user_id=_user.id,
                score=0
            )
        )

    return video_name


def gen_name(length: int) -> str:
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(length))
