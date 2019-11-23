#!/bin/bash

set -e

tempbotd_dir="/opt/tempbotd"
opt_tempbotd_module="anyping.py dnsping.py httping.py icmping.py"
opt_tempbotd_module="${opt_tempbotd_module} weather.py eventlogger.py"

docker_image="tempbot:test"
docker_container="test_tempbot"

install_tempbot() {
    install -o root -g root -m 755 -D -d ${tempbotd_dir}
    install -o root -g root -m 644 ${opt_tempbotd_module} ${tempbotd_dir}
    install -o root -g root -m 755 tempbotd.py ${tempbotd_dir}
    install -o root -g root -m 644 anyping-sample.conf ${tempbotd_dir}

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

Install tempbotd as systemd service
$ sudo systemctl daemon-reload

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
    cd ${tempbotd_dir} && rm -f ${opt_tempbotd_module} \
                             tempbotd.py \
                             anyping-sample.conf \
                             anyping.conf
    rmdir ${tempbotd_dir}
}

initialize_docker() {
    # collect scripts into tar.gz
    mkdir -p tmp
    tar zcf tmp/files.tar.gz $(git ls-files) pytest.ini

    # build docker image
    (cd test; docker image build -t ${docker_image} -f Dockerfile.test .)

    # run docker container and install tempbot
    docker run -itd --rm --env-file=test/test.env --name ${docker_container} ${docker_image}
    docker cp tmp/files.tar.gz ${docker_container}:/tmp/
    docker exec ${docker_container} /bin/bash \
           -c 'mkdir -p /root/project/tempbotd && tar zxf /tmp/files.tar.gz -C /root/project/tempbotd'
    docker exec ${docker_container} /bin/bash -c 'cd tempbotd && /bin/bash install.sh install'
    docker exec ${docker_container} /bin/bash -c 'cd /opt/tempbotd && cp anyping-sample.conf anyping.conf'
    if [ -f anyping.conf ]; then
        docker cp anyping.conf ${docker_container}:/tmp/
        docker exec ${docker_container} /bin/bash -c 'cd /opt/tempbotd && cp /tmp/anyping.conf . && chmod 644 anyping.conf'
    fi

    # set signal handler
    trap "docker stop ${docker_container}" SIGINT SIGHUP
}

test_on_docker() {
    initialize_docker
    # run test
    docker exec ${docker_container} /bin/bash -c 'cd tempbotd && python3 -m pytest test'
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

