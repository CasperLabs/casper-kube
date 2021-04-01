FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive 

RUN apt update
RUN apt -y install curl iputils-ping telnet vim strace valgrind awscli lsof htop net-tools jq
RUN rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY init.sh /init.sh

CMD /init.sh

