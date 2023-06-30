from typing import List

from fastapi import APIRouter, Request

import src.schemas
from src.models import user_action, user, video, user_recommendation, direction, application

from src.db import database


router = APIRouter(
    prefix="/users",
    tags=['User']
)

from fastapi import HTTPException, FastAPI, Response, Depends
from uuid import UUID, uuid4

from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.session_verifier import SessionVerifier
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters

cookie_params = CookieParameters()

cookie = SessionCookie(
    cookie_name="cookie",
    identifier="general_verifier",
    auto_error=True,
    secret_key="DONOTUSE",
    cookie_params=cookie_params,

)
backend = InMemoryBackend[UUID, src.schemas.SessionData]()


class BasicVerifier(SessionVerifier[UUID, src.schemas.SessionData]):
    def __init__(
            self,
            *,
            identifier: str,
            auto_error: bool,
            backend: InMemoryBackend[UUID, src.schemas.SessionData],
            auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: src.schemas.SessionData) -> bool:
        """If the session exists, it is valid"""
        return True


verifier = BasicVerifier(
    identifier="general_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(status_code=403, detail="invalid session"),
)


@router.get("/hint/", dependencies=[Depends(cookie)], response_model=bool)
async def hint(session_data: src.schemas.SessionData = Depends(verifier)):
    _user = await database.fetch_one(
        query=user.select().where(user.c.uai == session_data.uai)
    )
    return _user.uses_number < 3


@router.get("/videos/", dependencies=[Depends(cookie)], response_model=List[src.schemas.Video])
async def videos(session_data: src.schemas.SessionData = Depends(verifier)):
    _user = await database.fetch_one(
        query=user.select().where(user.c.uai == session_data.uai)
    )

    _user_recommendations = await database.fetch_all(
        query=user_recommendation.select().where(
            user_recommendation.c.user_id == _user.id
        ).order_by(user_recommendation.c.score.desc())
    )

    _videos = [
        await database.fetch_one(
            query=video.select().where(video.c.id == _user_recommendation.video_id)
        )
        for _user_recommendation in _user_recommendations
    ]

    return _videos


@router.post("/")
async def create_user(user_in: src.schemas.UserIn):
    _user = await database.fetch_one(
        query=user.select().where(user.c.uai == user_in.uai)
    )
    _application = await database.fetch_one(
        query=application.select().where(application.c.token == user_in.token)
    )

    _videos = await database.fetch_all(query=video.select())

    if not _application:
        return {'id': None, 'message': 'Incorrect application token'}
    if not _user:
        user_id = await database.execute(
            user.insert().values(
                token=user_in.token,
                uai=user_in.uai,
                geo={
                    'lat': user_in.lat,
                    'lon': user_in.lon
                },
                uses_number=0
            )
        )
        for _video in _videos:
            await database.execute(
                user_recommendation.insert().values(
                    video_id=_video.id,
                    user_id=user_id,
                    score=0
                )
            )
        return {'id': user_id}

    return {'id': _user.id, 'message': 'the user already exists'}


@router.post("/choice/", dependencies=[Depends(cookie)])
async def choice(video_name: str, dir: int, session_data: src.schemas.SessionData = Depends(verifier)):
    '''
    :param video_name:
    :param dir:
        1    "up"
        2    "down"
        3    "left"
        4    "right"
    :param session_data:
    :return:
    '''

    _direction = await database.fetch_one(
        query=direction.select().where(
            (direction.c.id == dir)
        )
    )

    _user = await database.fetch_one(
        query=user.select().where(user.c.uai == session_data.uai)
    )

    _video = await database.fetch_one(
        query=video.select().where(video.c.name == video_name)
    )

    _user_recommendation = await database.fetch_one(
        query=user_recommendation.select().where(
            (user_recommendation.c.video_id == _video.id) &
            (user_recommendation.c.user_id == _user.id)
        )
    )

    if _user_recommendation:
        await database.execute(
            query=user_recommendation.update().values(
                score=user_recommendation.c.score + _direction.ratio
            ).where(
                (user_recommendation.c.video_id == _video.id) &
                (user_recommendation.c.user_id == _user.id)
            )
        )
    else:
        await database.execute(
            query=user_recommendation.insert().values(
                video_id=_video.id,
                user_id=_user.id,
                score=_direction.ratio
            )
        )

    user_action_id = await database.execute(
        query=user_action.insert().values(
            video_id=_video.id,
            user_id=_user.id,
            direction=dir
        )
    )

    return {"id": user_action_id}


@router.post("/create_session/{uai}")
async def create_session(uai: str, response: Response):
    _user = await database.fetch_one(
        query=user.select().where(user.c.uai == uai)
    )

    if _user is None:
        return f"user not found"

    session = uuid4()
    data = src.schemas.SessionData(uai=uai)

    await backend.create(session, data)
    cookie.attach_to_response(response, session)

    await database.execute( 
        query=user.update().values(
            uses_number=_user.uses_number+1
        ).where(user.c.uai == uai)
    )

    return f"created session for {uai}"


@router.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: src.schemas.SessionData = Depends(verifier)):
    return session_data


@router.post("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"
