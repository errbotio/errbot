FROM python:3.9-slim as build
WORKDIR /wheel
COPY . .
RUN apt update && apt install -y build-essential git
RUN pip3 wheel --wheel-dir=/wheel \
    wheel . .[irc] .[XMPP] .[telegram] errbot-backend-slackv3

FROM python:3.9-slim as base
COPY --from=build /wheel /wheel
RUN apt update && \
    apt install -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel \
    . .[irc] .[XMPP] .[telegram] errbot-backend-slackv3 && \
    rm -rf /wheel /var/lib/apt/lists/*
RUN useradd -m errbot

FROM base
EXPOSE 3141 3142
VOLUME /home/errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init
ENTRYPOINT [ "/usr/local/bin/errbot" ]
