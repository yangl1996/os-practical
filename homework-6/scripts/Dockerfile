FROM alpine:3.6
RUN apk update                                              # get package index
RUN apk add openssh
RUN mkdir -p /var/run/sshd                                  # sshd run dir
RUN apk add python3                                         # depended by jupyter
RUN apk add python3-dev musl-dev gcc g++                    # depended by pyzmq
RUN pip3 install jupyter                                    # install jupyter using pip
RUN apk add openssl                                         # github release is https
RUN wget 'https://github.com/coreos/etcd/releases/download/v3.1.8/etcd-v3.1.8-linux-amd64.tar.gz' && tar xf etcd-v3.1.8-linux-amd64.tar.gz && cd etcd-v3.1.8-linux-amd64 && cp etcd* /usr/local/bin                       			# install etcd
RUN mkdir -p /root/sharedfiles                              # glusterfs mount point
ADD scripts/ /root/scripts/
CMD ["/bin/sh", "/root/scripts/pulse.sh"]