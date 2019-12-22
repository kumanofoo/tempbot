FROM python:3-buster

COPY ./requirements.txt /tmp
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
RUN pip3 install --no-cache-dir pytest pytest-mock

# change openssl security level in buster
COPY ./openssl.cnf /tmp
RUN /bin/bash -c 'grep -F -s 10. /etc/debian_version > /dev/null && \
                  cp /tmp/openssl.cnf /etc/ssl'

WORKDIR /root/project

# pusedo temperature sensor
COPY ./w1_slave.py /root/project

CMD ["/bin/bash"]
