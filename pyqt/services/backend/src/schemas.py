from pydantic import BaseModel, Json


class Video(BaseModel):
    id: int
    name: str

class UserIn(BaseModel):
    token: str
    uai: str
    lat: float
    lon: float


class ApplicationIn(BaseModel):
    token: str
    name: str

class SessionData(BaseModel):
    uai: str
