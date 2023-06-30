FROM python:3.9

RUN mkdir app
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

COPY ./requirements.txt /app/requirements.txt

# install psycopg2 dependencies

RUN apt-get update \
    && apt-get -y install libpq-dev gcc 

RUN pip install --upgrade pip
RUN pip install -r requirements.txt


COPY ./src /app/src