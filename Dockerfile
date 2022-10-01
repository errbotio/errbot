# syntax=docker/dockerfile:1.4

ARG BASE_IMAGE=python:3.9-slim
FROM ${BASE_IMAGE} AS build
WORKDIR /wheel
COPY . .
RUN apt update && apt install -y build-essential git
RUN cd /tmp && \
    git clone https://github.com/errbotio/err-backend-slackv3 slackv3
RUN pip3 wheel --wheel-dir=/wheel . \
      -r /tmp/slackv3/requirements.txt wheel \
      errbot errbot[irc] errbot[XMPP] errbot[telegram] && \
    cp /tmp/slackv3/requirements.txt /wheel/slackv3-requirements.txt

FROM ${BASE_IMAGE} AS base
RUN --mount=type=bind,from=build,source=/wheel,target=/wheell,rw \
    apt update && \
    apt install --no-install-recommends -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel . \
      -r /wheel/slackv3-requirements.txt \
      errbot errbot[irc] errbot[XMPP] errbot[telegram] && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* && \
    useradd -m errbot

FROM base
EXPOSE 3141 3142
VOLUME /home/errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init && \
    git clone --depth=1 https://github.com/errbotio/err-backend-slackv3 backend-plugins/slackv3
ENTRYPOINT [ "/usr/local/bin/errbot" ]
