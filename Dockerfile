FROM tipsi/base_python:1.0.6

WORKDIR /code

RUN pip3 install git+https://github.com/nicoddemus/pytest.git@8c9efd86087c36dda54cbe5284c1f804688bd443 pytest-asyncio
RUN apt install -y tcpdump

ADD . /code
WORKDIR /code
