FROM fan0/python:3.0.2

WORKDIR /code

RUN pip3 install fan_tools pytest-asyncio pytest-cov codecov
RUN apt install -y tcpdump

ADD . /code
WORKDIR /code
