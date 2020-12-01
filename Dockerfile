FROM python:3.8-slim as BUILD
WORKDIR /wheel
COPY . .
RUN pip3 wheel --wheel-dir=/wheel \
    errbot errbot[irc] errbot[slack] errbot[XMPP] errbot[telegram]

FROM python:3.8-slim
COPY --from=BUILD /wheel /wheel
RUN apt update && \
    apt install -y git && \
    cd /wheel && \
    pip3 -vv install --no-index --find-links /wheel \
    errbot errbot[irc] errbot[slack] errbot[XMPP] errbot[telegram] && \
    rm -rf /wheel /var/lib/apt/lists/*

RUN useradd -m errbot
USER errbot
EXPOSE 3141 3142
WORKDIR /home/errbot
ENTRYPOINT [ "/usr/local/bin/errbot" ]
