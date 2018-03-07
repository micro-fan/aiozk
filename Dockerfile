FROM tipsi/base_python:1.0.3

WORKDIR /code

RUN pip3 install pytest pytest-asyncio
RUN apt install -y tcpdump

ADD . /code
WORKDIR /code
