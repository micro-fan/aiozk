FROM tipsi/base_python:1.0.6

WORKDIR /code

RUN pip3 install pytest==3.6.* pytest-asyncio asynctest
RUN apt install -y tcpdump

ADD . /code
WORKDIR /code
