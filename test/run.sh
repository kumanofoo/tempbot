#!/bin/bash


if [ $# = 0 ]; then
    # run tempbotd.py
    docker_command='python3 /opt/tempbotd/tempbotd.py'
elif [ "x$1" = "xtest" ]; then
    # run pytest
    docker_command='cd tempbotd && python3 -m pytest test'
elif [ "x$1" = "xclean" ]; then
    # stop container
    container=$(docker ps | grep -c 'test_tempbot')
    if [ $container = 1 ]; then
        docker stop test_tempbot
    fi
    exit 0
else
    echo "Usage: run.sh [test|clean]"
    exit 1
fi


# collect source code into tar.gz
mkdir -p tmp
tar zcf tmp/files.tar.gz $(git ls-files)

# build docker container
(cd test; docker image build -t tempbot:test -f Dockerfile.test .)

# run docker container and install tempbot
docker run -itd --rm --env-file=test/test.env --name test_tempbot tempbot:test
docker cp tmp/files.tar.gz test_tempbot:/tmp/
docker exec test_tempbot /bin/bash -c 'mkdir -p /root/project/tempbotd && tar zxf /tmp/files.tar.gz -C /root/project/tempbotd'
docker exec test_tempbot /bin/bash -c 'cd tempbotd && /bin/bash install.sh'

# signal handler
trap 'docker stop test_tempbot' SIGINT SIGHUP

# execute command
docker exec test_tempbot /bin/bash -c "${docker_command}"
