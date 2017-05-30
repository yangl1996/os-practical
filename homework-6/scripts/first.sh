ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa    # generate host key pair
ssh-keygen -f /root/.ssh/id_rsa -N '' -t rsa            # generate client key pair
/usr/sbin/sshd                                          # start sshd
cat /root/.ssh/id_rsa.pub >> /root/sharedfiles/pubkeys  # gather public keys
myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
etcd --name $myip --initial-advertise-peer-urls http://$myip:2380 \
--listen-peer-urls http://$myip:2380 \
--listen-client-urls http://$myip:2379,http://127.0.0.1:2379 \
--advertise-client-urls http://$myip:2379 \
--initial-cluster-token mesos \
--initial-cluster 192.0.2.100=http://192.0.2.100:2380,192.0.2.101=http://192.0.2.101:2380,192.0.2.102=http://192.0.2.102:2380 \
--initial-cluster-state new
ln -s /root/sharedfiles/pubkeys /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys