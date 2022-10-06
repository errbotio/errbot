# syntax=docker/dockerfile:1.4

ARG BASE_IMAGE=python:3.9-slim
ARG INSTALL_EXTRAS=irc,XMPP,telegram
ARG SLACKV3_VERSION=0.2.1

FROM ${BASE_IMAGE} AS build
ARG INSTALL_EXTRAS
ARG SLACKV3_VERSION
WORKDIR /wheel
COPY . .
RUN apt update && apt install -y build-essential git
RUN cd /tmp && \
    git clone --depth=1 -b v${SLACKV3_VERSION} https://github.com/errbotio/err-backend-slackv3 slackv3
RUN pip3 wheel --wheel-dir=/wheel . \
      -e /tmp/slackv3 wheel \
      errbot errbot[${INSTALL_EXTRAS}]

FROM ${BASE_IMAGE} AS base
ARG INSTALL_EXTRAS
ARG SLACKV3_VERSION
RUN --mount=type=bind,from=build,source=/wheel,target=/wheel,rw \
    apt update && \
    apt install --no-install-recommends -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel . \
      errbot errbot[${INSTALL_EXTRAS}] errbot-backend-slackv3 && \
    git clone --depth=1 -b v${SLACKV3_VERSION} \
      https://github.com/errbotio/err-backend-slackv3 \
      /usr/local/lib/python3.9/site-packages/errbot/backends/slackv3 && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    useradd -m errbot

FROM base
EXPOSE 3141 3142
VOLUME /home/errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init
STOPSIGNAL SIGINT
ENTRYPOINT [ "/usr/local/bin/errbot" ]
