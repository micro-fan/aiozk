FROM ghcr.io/micro-fan/python:4.7.0-py3.13

WORKDIR /code

RUN pip3 install fan_tools pytest-asyncio pytest-cov codecov

ADD . /code
WORKDIR /code
