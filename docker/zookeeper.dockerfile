FROM ubuntu
MAINTAINER cybergrind@gmail.com

RUN apt update && apt install -y \
        curl \
        libyaml-dev \
        default-jdk-headless \
        python3-dev \
        python3-pip

ENV ZOOKEEPER_VERSION 3.5.2-alpha
RUN curl -sS http://ftp.byfly.by/pub/apache.org/zookeeper/zookeeper-${ZOOKEEPER_VERSION}/zookeeper-${ZOOKEEPER_VERSION}.tar.gz | tar -xzf - -C /opt \
  && mv /opt/zookeeper-* /opt/zookeeper \
  && chown -R root:root /opt/zookeeper

RUN pip3 install tipsi_tools aiozk docker-py

VOLUME ["/srv/zookeeper"]
ADD ./docker/zk_start.py /
ADD ./docker/zoo.cfg /opt/zookeeper/conf/
RUN chmod a+x /zk_start.py && ln -s /opt/zookeeper/bin/zkCli.sh /usr/bin/zk
CMD ./zk_start.py
