#!/bin/bash

set -e

tempbotd_dir="/opt/tempbotd"

docker_image="tempbot:test"
docker_container="test_tempbot"

install_tempbot() {
    install -o root -g root -m 755 -D -d ${tempbotd_dir}/tempbotlib
    install -o root -g root -m 644 tempbotlib/* ${tempbotd_dir}/tempbotlib
    install -o root -g root -m 755 tempbotd.py ${tempbotd_dir}
    install -o root -g root -m 644 tempbot-sample.conf ${tempbotd_dir}

    if [ -f /etc/default/tempbot ]; then
        echo skip install /etc/default/tempbot
    else
        install -o root -g root -m 600 tempbot /etc/default
    fi

    if [ -f /etc/systemd/system/tempbotd.service ]; then
        echo skip install /etc/systemd/system/tempbotd.service
    else
        install -o root -g root -m 644 \
                tempbotd.service \
                /etc/systemd/system
    fi


    cat <<EOF

Start tempbotd service
$ sodo systemctl start tempbotd

Check tempbotd service
$ systemctl status tempbotd

Enable to start tempbotd service on system boot 
$ sudo systemctl enable tempbotd

EOF
}

uninstall_tempbot() {
    read -p "Are you sure (yes/NO)? " reply
    case "${reply}" in
        yes)
            ;;
        *)
            echo canceled
            exit 1
            ;;
    esac

    systemctl stop tempbotd
    systemctl disable tempbotd
    rm /etc/systemd/system/tempbotd.service
    rm /etc/default/tempbot
    cd ${tempbotd_dir} && rm -r tempbotlib \
                             tempbotd.py \
                             tempbot-sample.conf \
                             tempbot.conf
    rmdir ${tempbotd_dir}
}

initialize_docker() {
    # collect scripts into tar.gz
    mkdir -p tmp
    tar zcf tmp/files.tar.gz $(git ls-files)

    # build docker image
    cp requirements.txt tests
    (cd tests; docker image build -t ${docker_image} -f Dockerfile .)
    rm tests/requirements.txt

    # run docker container and install tempbot
    docker run -itd --rm --env-file=tests/test.env --name ${docker_container} ${docker_image}
    docker cp tmp/files.tar.gz ${docker_container}:/tmp/
    docker exec ${docker_container} /bin/bash \
           -c 'mkdir -p /root/project/tempbotd && tar zxf /tmp/files.tar.gz -C /root/project/tempbotd'
    docker exec ${docker_container} /bin/bash -c 'cd tempbotd && /bin/bash install.sh install'
    docker exec ${docker_container} /bin/bash -c 'cd /opt/tempbotd && cp tempbot-sample.conf tempbot.conf'
    if [ -f tempbot.conf ]; then
        docker cp tempbot.conf ${docker_container}:/tmp/
        docker exec ${docker_container} /bin/bash -c 'cd /opt/tempbotd && cp /tmp/tempbot.conf . && chmod 644 tempbot.conf'
    fi
    docker exec -d ${docker_container} python3 w1_slave.py

    # set signal handler
    trap "docker stop ${docker_container}" SIGINT SIGHUP
}

test_on_docker() {
    initialize_docker
    # run test
    docker exec ${docker_container} /bin/bash -c 'cd tempbotd && python3 -m pytest --cov=tempbotlib tests'
    stop_docker
}

run_on_docker() {
    initialize_docker
    # run tempbotd
    docker exec ${docker_container} /bin/bash -c 'python3 /opt/tempbotd/tempbotd.py'
    stop_docker
}

stop_docker() {
    container=$(docker ps | grep -c 'test_tempbot')
    if [ $container = 1 ]; then
        docker stop ${docker_container}
    fi
}

usage() {
    echo "usage: ${0##*/} [install|uninstall|test|run|stop-docker]"
}

case "$1" in
    install)
        install_tempbot
        ;;
    uninstall)
        uninstall_tempbot
        ;;
    test)
        test_on_docker
        ;;
    run)
        run_on_docker
        ;;
    stop-docker)
        stop_docker
        ;;
    *)
        usage
        ;;
esac

exit 0

