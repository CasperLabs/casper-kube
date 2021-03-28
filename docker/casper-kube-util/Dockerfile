FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt update
RUN apt -y install iputils-ping telnet curl strace htop vim git lsof awscli net-tools
RUN apt -y install wget

RUN rm -rf /var/lib/{apt,dpkg,cache,log}/

RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.1/zsh-in-docker.sh)" -- \
    -p git \
    -t robbyrussell
RUN usermod --shell /bin/zsh root


RUN mkdir /casper-node

COPY init.sh /init.sh

WORKDIR /casper-node
CMD /init.sh
