FROM fan0/python:4.0.1

WORKDIR /code

RUN pip3 install fan_tools pytest-asyncio pytest-cov codecov

ADD . /code
WORKDIR /code
