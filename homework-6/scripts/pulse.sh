myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
nohup sh /root/scripts/first.sh &
while :
do
    etcdctl set --ttl 60 -- $myip 'isAlive'
    echo '127.0.0.1 localhost' > /etc/hosts
    peerindex=0
    etcdctl ls --sort / | sed 's/^.\{1\}//g' | while read -r peer ;
    do
        echo "$peer node$peerindex" >> /etc/hosts
        peerindex=`expr $peerindex + 1`
    done
    etcdctl member list | grep "name=$myip.*isLeader=true"
    if [ $? -eq 0 ]; then
        # is leader
        netstat -nlp | grep 8888
        if [ $? -ne 0 ]; then
            # jupyter not on
            jupyter notebook --allow-root --ip='*' --no-browser &
        fi
    fi
    sleep 40
done
