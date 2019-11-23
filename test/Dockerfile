FROM debian:buster
RUN apt-get update && \
    apt-get install -y \
      git python3 python3-pip python3-dnspython python3-matplotlib python3-pytest && \
    apt-get clean && \
    pip3 install \
      slackclient==1.3.2

WORKDIR /root/project
ADD ./w1_slave /tmp/w1_slave

RUN ["git", "clone", "https://github.com/kumanofoo/tempbot.git"]

WORKDIR /root/project/tempbot
RUN ["/bin/bash", "./install.sh"]

CMD ["python3", "/opt/tempbotd/tempbotd.py"]
