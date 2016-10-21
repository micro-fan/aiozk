FROM ubuntu:xenial

RUN apt-get update && \
    apt-get install -y git \
                       python3-pip \
                       python3.5

RUN update-alternatives --install /usr/bin/python3 python3.5 /usr/bin/python3.5 0

WORKDIR /code

RUN pip3 install nose2


ADD . /code
WORKDIR /code
