# This builds a docker image running errbot.

FROM python:3-slim
MAINTAINER Guillaume Binet

# Note: The config.py and data will be a volume mounted to /var/lib/err
#
# For example if you want to configure and store the state of err in /home/gbin/err:
# copy config.py in /home/gbin/err
# start the docker container with :
# docker run -v /home/gbin/err:/var/lib/err err
# be sure in your config.py to have all the persistent data pointing to it for example:
# BOT_DATA_DIR = '/var/lib/err'
# BOT_LOG_FILE = '/var/lib/err/err.log'
# BOT_EXTRA_PLUGIN_DIR = '/usr/lib/err/extra'

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install gcc git autoconf automake libtool gnulib libffi-dev libssl-dev

# optional dependencies (support for everything)

# native dependencies for Tox
WORKDIR /usr/src
RUN git clone https://github.com/jedisct1/libsodium.git && cd libsodium && ./autogen.sh && ./configure && make && make install && cd .. && rm -Rf libsodium
RUN git clone https://github.com/irungentoo/toxcore.git && cd toxcore && ./autogen.sh && ./configure && make && make install && cd .. && rm -Rf toxcore
RUN git clone https://github.com/aitjcize/PyTox.git && cd PyTox && python ./setup.py install && cd .. && rm -Rf PyTox

# TODO: pyfire fails
RUN pip install sleekxmpp pyasn1 pyasn1-modules irc hypchat

# err itself
RUN git clone https://github.com/gbin/err.git && cd err && python ./setup.py install && cd .. && rm -Rf err

# run part
WORKDIR /var/lib/err
VOLUME /var/lib/err
ENV LD_LIBRARY_PATH /usr/local/lib
# serverless default backend, run it with docker run --entrypoint "err.py --xxx" err to override it.
ENTRYPOINT [ "err.py", "--tox"]
