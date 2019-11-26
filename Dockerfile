FROM fan0/python:2.1.0

WORKDIR /code

RUN pip3 install fan_tools pytest-asyncio asynctest
RUN apt install -y tcpdump

ADD . /code
WORKDIR /code
