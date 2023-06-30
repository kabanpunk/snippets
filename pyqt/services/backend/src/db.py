import sqlalchemy
import databases
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    DATABASE_URL,
    echo=True
)


def create_all():
    metadata.create_all(engine)
