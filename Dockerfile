FROM python:3.9-slim as BUILD
WORKDIR /wheel
COPY . .
RUN apt update && apt install build-essential -y
RUN pip3 wheel --wheel-dir=/wheel . \
    errbot errbot[irc] errbot[slack] errbot[XMPP] errbot[telegram]

FROM python:3.9-slim
COPY --from=BUILD /wheel /wheel
RUN apt update && \
    apt install -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel . \
    errbot errbot[irc] errbot[slack] errbot[XMPP] errbot[telegram] && \
    rm -rf /wheel /var/lib/apt/lists/*

RUN useradd -m errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init
EXPOSE 3141 3142
VOLUME /home/errbot
ENTRYPOINT [ "/usr/local/bin/errbot" ]
