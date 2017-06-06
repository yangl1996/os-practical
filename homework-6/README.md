# 第六次作业

## Paxos 算法

Paxos 算法中规定了如下三个角色：Proposer、Acceptor 和 Learner。Proposer 可以提出提案，包含提案编号和对应的 value。Acceptor 收到之后可以 accept 提案，若提案得到多数 acceptor 通过，该提案就被批准，learner 会学习被批准的提案。Paxos 算法的一次运行中，仅通过一个提案。

算法运行分成两个阶段：准备阶段和批准阶段。

### 准备阶段

Proposer 选择一个提案编号 n，这个编号 n 大于它之前使用过的所有编号。然后 proposer 给 acceptor 中半数以上的人发送准备请求。

对于每一个 acceptor，如果收到的请求的提案编号 n 大于之前收到的所有提案编号，那该 acceptor 将返回一个信息，承诺之后会拒绝所有编号小于 n 的提案。同时，acceptor 还将返回之前接受过的提案的编号和对应的值。

### 批准阶段

如果 proposer 收到了足够多的承诺，他需要给这个提案设置一个值。如果有 acceptor 告诉 proposer 曾经的提案编号和对应的值，那他需要从中选取提案编号最大的对应的那个值，然后设置成自己的提案的值。如果没有之前的提案，那 proposer 可以自由设置值。之后，proposer 会把这个值发送给半数以上的 acceptor。

对于每一个 acceptor，如果他之前没有对更大的提案编号做过承诺，那他将向 proposer 和所有 learner 发送“接受”。如果一个 proposer 收到超过半数的接受信息，那说明这个提案被接受了。同时，当一个 learner 收到超过半数的接受信息，它也将更新自己这边对应的值。

## Raft 协议

场景：有五个节点（A、B、C、D、E）的系统，运行 Raft 协议。初始状态没有任何 leader。

```
Lengend
----------------------------------
(X)	Pending change X
_X	Committed change X
X*	Leader with committed change X
----------------------------------

时间	A	B	C	D	E	事件
0						A Elect Timer 时间到，发送 Election 请求
1	*					A 收到半数以上 vote，当上 leader
2	_X*					A 收到客户端更新请求（X）
3	_X*	_X	_X	_X	_X	A 把这一请求转发给其他节点
4	X*	_X	_X	_X	_X	A 收到半数以上节点的确认，将改动 commit
5	X*	X	X	X	X	A 要求其他节点也 commit
6	_Y*	X	X	X	X	A 收到请求（Y）
7	_Y*	_Y	X	X	X	A 把这一请求转发给其他节点，此时 AB 和 CDE 分开
8 	_Y*	_Y	X	X	X	A 始终无法 commit 改动，因为没有收到半数以上确认
9	_Y*	_Y	_Y	_Y	_Y	网络恢复，A 的改动请求被 CDE 收到
10	Y*	_Y	_Y	_Y	_Y	收到半数以上的确认，A 将改动 commit
```
## Mesos 的容错机制

Mesos 的 single-point-of-failure 是 master 节点。一旦 master 节点失效，之后就无法进行 resource allocation，框架就无法开始新的 job 了。因此，有必要确保 master 的高可用性，在一个 master 下线的时候自动起一个新的 master，并自动配置 worker，让它们自动和这个新的 master 联系。

Mesos 目前支持使用 ZooKeeper 自动选举 master 并通知整个集群当前 master 节点的地址（基于 etcd 的选项正在开发中）。下面将配置 Mesos 使用 ZooKeeper，并搭建 ZooKeeper Cluster 和 Mesos Cluster。

首先给每个节点配置 unique 的 ZooKeeper Node ID。

```bash
echo 1 > /etc/zookeeper/conf/myid
echo 'server.1=172.16.6.107:2888:3888' >> /etc/zookeeper/conf/zoo.cfg
echo 'server.2=172.16.6.205:2888:3888' >> /etc/zookeeper/conf/zoo.cfg
echo 'zk://172.16.6.107:2181,172.16.6.205:2181/mesos' > /etc/mesos/zk
echo 1 > /etc/mesos-master/quorum
echo 172.16.6.107 > /etc/mesos-master/ip
cp /etc/mesos-master/ip /etc/mesos-master/hostname
```

然后启动服务。但是 ZooKeeper 的 systemd unit 貌似没有用。结合上一次被 Mesosphere 坑得 dpkg 的 database 都炸了的经历，可以看出这些 __bloatware__ 的打包质量都极差。最后在前台启动 ZooKeeper 发现它报了个 Error，然而无论是他给的脚本还是 systemd unit 都完全看不出迹象，都报告正常启动。在尝试胡乱安装 JDK 之后，我放弃了 Ubuntu。最后在两台 Arch 虚拟机上成功配置。在关掉一台之后，另一台会自动起来，之后查询 ZooKeeper 都会导向新的这一台，实现了高可用。

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
