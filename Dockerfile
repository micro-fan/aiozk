FROM ubuntu:bionic

RUN apt-get update && \
    apt-get install -y git \
                       python3-pip \
                       python3.6

RUN update-alternatives --install /usr/bin/python3 python3.6 /usr/bin/python3.6 0

WORKDIR /code

RUN pip3 install pytest tipsi_tools==1.5.0 pytest-asyncio

RUN apt install -y tcpdump
ADD . /code
WORKDIR /code
