FROM debian:stretch
RUN apt-get update && \
    apt-get install -y \
      git bats python3 python3-pip python3-dnspython python3-matplotlib python3-pytest && \
    apt-get clean && \
    pip3 install \
      slackclient websocket-client

WORKDIR /root/project
RUN git clone https://github.com/kumanofoo/tempbot.git
RUN cd ./tempbot && ./install.sh

CMD ["python3", "/opt/tempbotd/tempbotd.py"]