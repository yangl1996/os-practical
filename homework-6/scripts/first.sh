ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa    # generate host key pair
ssh-keygen -f /root/.ssh/id_rsa -N '' -t rsa            # generate client key pair
/usr/sbin/sshd                                          # start sshd
cat /root/.ssh/id_rsa.pub >> /root/sharedfiles/pubkeys  # gather public keys
myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
etcd --name $myip --initial-advertise-peer-urls http://$myip:2380 \
--listen-peer-urls http://0.0.0.0:2380 \
--listen-client-urls http://0.0.0.0:2379 \
--advertise-client-urls http://$myip:2379 \
--initial-cluster-token mesos \
--initial-cluster 192.0.3.100=http://192.0.3.100:2380,192.0.3.101=http://192.0.3.101:2380,192.0.3.102=http://192.0.3.102:2380 \
--initial-cluster-state new
ln -s /root/sharedfiles/pubkeys /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys