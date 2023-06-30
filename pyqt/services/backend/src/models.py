from sqlalchemy import Table, Column, ForeignKey, DateTime
from sqlalchemy import Integer, String, JSON, Float, Boolean
from sqlalchemy.sql import func

from src.db import metadata

user = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("token", String),
    Column("uai", String),
    Column("creation_time", DateTime(timezone=True), server_default=func.now()),
    Column("uses_number", Integer),
    Column("geo", JSON)
)

video = Table(
    "video",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String)
)

direction = Table(
    "direction",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("ratio", Float)
)

user_action = Table(
    "user_action",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("video.id")),
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("direction", Integer, ForeignKey("direction.id")),
    Column("datetime", DateTime(timezone=True), server_default=func.now())
)


user_recommendation = Table(
    "user_recommendation",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("video_id", Integer, ForeignKey("video.id")),
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("score", Float),
)

application = Table(
    "application",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("token", String),
    Column("name", String)
)

