FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /usr/src/app

RUN apt update && apt install -y python3-pip && apt install -y gettext
SHELL ["/bin/bash", "-c"]
RUN mkdir -p /usr/src/app/public
RUN mkdir -p /usr/src/app/log
COPY ./requirements.prod.txt ./requirements.txt
RUN apt update && apt install -y python3-pip && apt install -y gettext        \
    && pip3 install -r requirements.txt                                       \
    && apt remove -y python3-pip                                              \
    && apt autoremove --purge -y                                              \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY . .
COPY ./deploy/initapp.sh .
RUN  chmod 775 ./initapp.sh
COPY ./deploy/generate_enc_key.py .
RUN  chmod 775 ./generate_enc_key.py
RUN rm -rf ./deploy
