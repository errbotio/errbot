ARG BASE_IMAGE=python:3.9-slim
ARG INSTALL_EXTRAS=irc,XMPP,telegram,slack

FROM ${BASE_IMAGE} AS build
ARG INSTALL_EXTRAS
WORKDIR /wheel
COPY . .
RUN apt update && apt install -y build-essential git
RUN pip3 wheel --wheel-dir=/wheel \
    wheel . .[${INSTALL_EXTRAS}] errbot-backend-slackv3

FROM ${BASE_IMAGE} AS base
ARG INSTALL_EXTRAS
COPY --from=build /wheel /wheel
RUN apt update && \
    apt install -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel \
    errbot errbot[${INSTALL_EXTRAS}] errbot-backend-slackv3 && \
    rm -rf /wheel /var/lib/apt/lists/*
RUN useradd -m errbot

FROM base
EXPOSE 3141 3142
VOLUME /home/errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init
STOPSIGNAL SIGINT
ENTRYPOINT [ "/usr/local/bin/errbot" ]
