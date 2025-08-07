FROM ghcr.io/micro-fan/python:4.7.0-py3.13
LABEL org.opencontainers.image.authors="cybergrind@gmail.com"

WORKDIR /
RUN apt update && apt install -y \
        curl \
        libyaml-dev \
        default-jdk-headless

ENV ZOOKEEPER_VERSION 3.9.2
ENV ZOOKEEPER_PACKAGE apache-zookeeper-${ZOOKEEPER_VERSION}-bin
RUN curl -sS https://archive.apache.org/dist/zookeeper/zookeeper-${ZOOKEEPER_VERSION}/${ZOOKEEPER_PACKAGE}.tar.gz | tar -xzf - -C /opt \
  && mv /opt/${ZOOKEEPER_PACKAGE} /opt/zookeeper \
  && chown -R root:root /opt/zookeeper

RUN pip3 install fan_tools aiozk docker-py

VOLUME ["/srv/zookeeper", "/opt/zookeeper/conf"]

ADD ./docker/zk /usr/bin/zk
ADD ./docker/zk_start.py /
ADD ./docker/zoo.cfg /opt/zookeeper/conf/
RUN chmod a+x /zk_start.py
CMD /zk_start.py
