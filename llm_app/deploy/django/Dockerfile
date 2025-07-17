FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /usr/src/app
COPY ./requirements.prod.txt ./requirements.txt
RUN apt update && apt install -y python3-pip && apt install -y gettext        \
    && pip3 install -r requirements.txt                                       \
    && apt remove -y python3-pip                                              \
    && apt autoremove --purge -y                                              \
    && rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list
COPY . .
COPY ./deploy/initapp.sh .
RUN rm -rf ./deploy
RUN mkdir -p /usr/src/app/public
RUN mkdir -p /usr/src/app/log
