FROM ubuntu
MAINTAINER cybergrind@gmail.com

RUN apt update && apt install -y \
        curl \
        libyaml-dev \
        default-jdk-headless \
        python3-dev \
        python3-pip

ENV ZOOKEEPER_VERSION 3.5.5
ENV ZOOKEEPER_PACKAGE apache-zookeeper-${ZOOKEEPER_VERSION}-bin
RUN curl -sS http://apache.mirrors.pair.com/zookeeper/zookeeper-${ZOOKEEPER_VERSION}/${ZOOKEEPER_PACKAGE}.tar.gz | tar -xzf - -C /opt \
  && mv /opt/${ZOOKEEPER_PACKAGE} /opt/zookeeper \
  && chown -R root:root /opt/zookeeper

RUN pip3 install tipsi_tools aiozk docker-py

VOLUME ["/srv/zookeeper", "/opt/zookeeper/conf"]

ADD ./docker/zk /usr/bin/zk
ADD ./docker/zk_start.py /
ADD ./docker/zoo.cfg /opt/zookeeper/conf/
RUN chmod a+x /zk_start.py
CMD ./zk_start.py
