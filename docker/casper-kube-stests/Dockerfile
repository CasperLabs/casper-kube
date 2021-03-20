FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt update
RUN apt -y install software-properties-common
RUN add-apt-repository -y ppa:deadsnakes/ppa

RUN apt update
RUN apt -y install iputils-ping telnet curl strace htop vim git lsof awscli redis
RUN apt -y install wget
RUN apt -y install python3.9
RUN rm -rf /var/lib/{apt,dpkg,cache,log}/

#set python3.9 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 2
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

RUN apt -y install python3-pip pipenv
RUN pip3 install pipx

#zsh
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.1/zsh-in-docker.sh)" -- \
    -p git \
    -t robbyrussell
RUN usermod --shell /bin/zsh root



RUN mkdir /casper-node

COPY init.sh /init.sh

WORKDIR /casper-node
CMD /init.sh
