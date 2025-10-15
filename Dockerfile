ARG INSTALL_EXTRAS=irc,XMPP,telegram,slack

FROM python:3.12 AS build
ARG INSTALL_EXTRAS

WORKDIR /wheel

COPY . .
RUN pip wheel --wheel-dir=/wheel wheel . .[${INSTALL_EXTRAS}]

FROM python:3.12-slim
ARG INSTALL_EXTRAS

RUN --mount=from=build,source=/wheel,target=/wheel \
    pip install --no-cache-dir --no-index --find-links /wheel \
    errbot errbot[${INSTALL_EXTRAS}]

RUN useradd --create-home --shell /bin/bash errbot
USER errbot
WORKDIR /home/errbot

RUN errbot --init

EXPOSE 3141 3142
VOLUME /home/errbot
STOPSIGNAL SIGINT

ENTRYPOINT [ "/usr/local/bin/errbot" ]
