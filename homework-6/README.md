# 第六次作业

## Paxos 算法

## Raft 协议

## Mesos 的容错机制

## 综合作业

### 搭建 Calico 容器网络

这一步和上一次作业完全一样。依次启动 host 上的 etcd、docker daemon、calico 并把 calico 网络添加到 docker 中。现在我我们得到一个名字为 “calico” 的 Docker network instance。之后的容器就将 attach 到这个网络之上。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/calicosetup.png?raw=true)

### 建立 GlusterFS 文件系统

这一步和第四次作业基本一样，需要在宿主机上创建 GlusterFS。首先启动 Gluster Server 然后互相 probe。之后创建新 volume，最后得到一个名字为 “glustervol” 的 GlusterFS Volume。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/glusterfssetup.png?raw=true)

然后两台 host 分别 mount 上。

```bash
sudo mount -t glusterfs 172.16.6.107:/glustervol /home/pkusei/gfsmount
```

### 准备 Docker Image

这一步准备好之后要运行的 Docker Image。这个 Docker Image 需要有 ssh client、JupyterNotebook、etcd，并能按照作业要求中说的自动在 etcd master 处在的容器中启动 JuypterNotebook。所以这次在 Alpine Linux 基础之上自行做一个 Docker Image。先把镜像 pull 下来，并起一个 container，用来 dry run。

```bash
sudo docker pull alpine:3.6
sudo docker run -it --rm alpine:3.6 /bin/ash
```

首先装上上述包。

```ash
apk update                                              # get package index

apk add openssh
mkdir -p /var/run/sshd                                  # sshd run dir

apk add python3                                         # depended by jupyter
apk add python3-dev musl-dev gcc g++                    # depended by pyzmq
pip3 install jupyter                                    # install jupyter using pip

apk add openssl                                         # github release is https
wget 'https://github.com/coreos/etcd/releases/download/v3.1.8/etcd-v3.1.8-li
nux-amd64.tar.gz' && \
tar xf etcd-v3.1.8-linux-amd64.tar.gz && \
cd etcd-v3.1.8-linux-amd64 && \
cp etcd* /usr/local/bin                                 # install etcd

mkdir -p /root/sharedfiles                              # glusterfs mount point
```

sshd 用如下脚本启动

```ash
ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa    # generate host key pair
ssh-keygen -f /root/.ssh/id_rsa -N '' -t rsa            # generate client key pair
/usr/sbin/sshd                                          # start sshd
cat /root/.ssh/id_rsa.pub >> /root/sharedfiles/pubkeys  # gather public keys
```

etcd 用如下脚本启动（自动获取本机 IP 并创建集群）

```ash
myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
etcd --name $myip --initial-advertise-peer-urls http://$myip:2380 \
--listen-peer-urls http://$myip:2380 \
--listen-client-urls http://$myip:2379,http://127.0.0.1:2379 \
--advertise-client-urls http://$myip:2379 \
--initial-cluster-token mesos \
--initial-cluster 192.0.2.100=http://192.0.2.100:2380,192.0.2.101=http://192.0.2.101:2380,192.0.2.102=http://192.0.2.102:2380 \
--initial-cluster-state new
```

### 使用 etcd

#### 确认自身是不是 Leader

这个可以通过比较 `etcdctl member list` 中的结果和自己的 IP 来确定。

```ash
myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
etcdctl member list | grep "name=$myip.*isLeader=true"
```

#### 监控机器是否在线

考虑使用 etcd 记录的 TTL，每台机器创建一个记录 `<$myip, isAlive>`，并设置 TTL。然后，机器不断刷新这一记录，向外界说明自己活着。用如下脚本不断重设记录：

```ash
while :
do
	myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`
	etcdctl set --ttl 60 -- $myip 'isAlive'
	sleep 40
done
```

然后只要

```ash
etcdctl ls --sort /
```

即可查看当前有哪些机器在线了，还是有序的。

### 做错误恢复

有了前面的 etcd，现在就可以完成要求的错误恢复。通过脚本定期检查上面的两项（自己是不是 Leader、有多少机器在线），就可以实现要求的功能。基本思路是：首先发送心跳包（刷新 key-value pair TTL）。并且查看当前所有在线机器，并刷新 `hosts` 文件。然后检查自己是不是 Leader，并检查 JupyterNotebook 是否已经起来（用 `netstat -nlp | grep 8888` 即可轻松检测），若两项都满足（即：自己是 Leader，但 Notebook 没起来）则启动 Notebook。

把上面的所有整合起来，得到一个简单的 shell 脚本：

```ash
myip=`ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p'`

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
```

所以说，只要在 container 启动时运行这个脚本就可以了。

### 使用 GlusterFS

为方便起见，我们把 GlusterFS 挂载在 host machine 上，然后用 Docker 的 data volume 功能映射到 container 里。一个好处就是不用处理网络问题（如果这里出现问题的话）。在 host machine 上，GlusterFS 被挂载在 `/home/pkusei/gfsmount`。它将被映射到 `/root/sharedfiles`。里面的 `pubkeys` 记录所有公钥。

然后建立软链接就行了。

```ash
ln -s /root/sharedfiles/pubkeys /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

### Put it together

把上面的内容全部整合，就得到了需要的所有脚本和一个 Docker File。详见 `scripts/`。成功 build Docker image。此次 Mesos Framework 可以直接用上一次的，而且不需要分两种情况（有 Notebook 和无 Notebook），而是只要从刚刚 build 完成的 image 起三个一样的 container 就 ok 了。

事实上，Framework 要执行的语义和下面的命令一样：

```ash
sudo docker run -it --net calico --ip 192.0.2.100 -v /home/pkusei/gfsmount:/root/sharedfiles --rm jpy
```

运行 Framework，可以发现功能、容错正常。

### 效果

#### Master 自动恢复

把原来是 Master 的机器 shutdown，在 TTL 过后，会自动在别的机器上启动 JupyterNotebook。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/master-relocate.png?raw=true)

#### hosts 自动 populate

`/etc/hosts` 会自动填充，并在有机器意外退出后刷新，保证 hostname 序号连续，并只包含可用的机器。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/hosts.png?raw=true)

下图是在一个节点挂掉之后。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/hosts-after-fail.png?raw=true)

#### 免密码登录

机器之间可以免密码登录。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/pwdless-login.png?raw=true)

#### 分布式文件系统

`/etc/sharedfiles` 是共享的分布式文件系统，它除了用于分发公钥，还可以用于一般的存储。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-6/attachments/sharedfile.png?raw=true)
