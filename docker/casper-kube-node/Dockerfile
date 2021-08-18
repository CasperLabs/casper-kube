FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive 

RUN apt update
RUN apt -y install curl iputils-ping telnet vim strace valgrind awscli lsof htop net-tools jq
RUN rm -rf /var/lib/{apt,dpkg,cache,log}/

# install basic required packages
RUN apt-get -y update
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y \
    sudo \
    wget \
    gnupg \
    tzdata \
    unzip \
    jq

# Install casper-node binaries
RUN sh -c 'echo "deb https://repo.casperlabs.io/releases" bionic main | tee -a /etc/apt/sources.list.d/casper.list'
RUN wget -q -O - https://repo.casperlabs.io/casper-repo-pubkey.asc | apt-key add -
RUN apt-get -y update
RUN apt-get install -y \
    casper-client \
    casper-node-launcher
    
COPY init.sh /init.sh

CMD /init.sh

