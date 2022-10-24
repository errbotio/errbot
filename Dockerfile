FROM python:3.9-slim as build
WORKDIR /wheel
COPY . .
RUN apt update && apt install -y build-essential git
RUN cd /tmp && \
    git clone https://github.com/errbotio/err-backend-slackv3 slackv3
RUN pip3 wheel --wheel-dir=/wheel . \
    -r /tmp/slackv3/test-requirements.txt wheel \
    errbot errbot[irc] errbot[XMPP] errbot[telegram] && \
    cp /tmp/slackv3/test-requirements.txt /wheel/slackv3-requirements.txt

FROM python:3.9-slim as base
COPY --from=build /wheel /wheel
RUN apt update && \
    apt install -y git && \
    cd /wheel && \
    pip3 -vv install --no-cache-dir --no-index --find-links /wheel . \
    -r /wheel/slackv3-requirements.txt \
    errbot errbot[irc] errbot[XMPP] errbot[telegram] && \
    rm -rf /wheel /var/lib/apt/lists/*
RUN useradd -m errbot

FROM base
EXPOSE 3141 3142
VOLUME /home/errbot
WORKDIR /home/errbot
USER errbot
RUN errbot --init
RUN git clone https://github.com/errbotio/err-backend-slackv3 backend-plugins/slackv3
ENTRYPOINT [ "/usr/local/bin/errbot" ]
