# 第五次作业

## 1 描述 Linux 内核对 IP 数据包的处理

IP 包从二层设备进入三层之后，在 kernel 内部处理流程中会遇到一些特定位置。在每一个特定位置，kernel 提供一个 hook，以便在这个位置对 IP 包做一些处理，如改动源地址、目标地址、丢弃该包，等等。IP 包每遇到一个 hook，都会被发送给 hook 到这里的程序，让它对 IP 包进行一些处理。下图描述了这些 hook 的位置。这一整个框架叫做 `netfilter`。`iptables` 就是利用了 `netfilter` 框架的一个内核模块及对应的用户空间程序。它 hook 到 kernel 内的这些特定位置，并允许用户控制其在各个位置的处理策略。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/bridge3a.png?raw=true)

可以看到，`netfilter` 一共有五个位置提供 hook，每个 hook 对应 `iptables` 的一个 `chain`（即对每个 IP 包在这里的一系列处理流程），分别是：

* `PREROUTING`，在 IP 包刚刚进入三层处理时（因此所有进入的包都会经过)
* `INPUT`，在 IP 包被确定是发给本机之后，在被本机更高层处理之前
* `FORWARD`，在 IP 包被确定需要继续转发并被路由后
* `OUTPUT`，在本机生成的 IP 包产生、路由之后
* `POSTROUTING`，在 IP 包完成所有处理，交由二层之前（因此所有要从网络设备上出去的包都会经过）

为了进一步方便用户使用，`iptables` 还提供更高层抽象的 `table`，每个 `table` 会在多个 `chain` 中安装处理规则，之间互相合作提供对应的功能。这些 `table` 有，

* `filter`，对应 `INPUT`、`FORWARD`、`OUTPUT`，在这些位置根据包的特征丢弃特定的包，实现类似防火墙、ACL 的作用，例如拒绝特定 IP 进入本机的包。
* `nat`，对应 `PREROUTING`、`OUTPUT`（DNAT）和 `INPUT`、`POSTROUTING`（SNAT），在这些位置修改 IP 包的源和目标地址，实现 NAT 的功能，例如在包发出的时候把目标地址改掉（`OUTPUT` 处理），并在对应地址发回的包中把源地址改掉（`PREROUTING` 处理），实现 DNAT。
* `mangle`，对应所有 `chain`，可以对包头进行杂七杂八的修改，例如修改 TTL、在包进下一步之前打一个 tag 之类的。
* `raw`，对应 `PREROUTING`、`OUTPUT`，在这些 IP 包可能“产生”的地方（即从外界进入、由本机生成）给包打 tag，要求 `iptables` 以无状态方式处理这些包（本来 `iptables` 会把包与连接相关联，消耗更多资源）。
* `security`，对应 `INPUT`、`FORWARD`、`OUTPUT`，用于给包打 tag，供 SELinux 使用。

这些 `table` 互相之间也有优先级，在同一个 `chain` 中，高优先级 `table` 安装的处理规则会优先执行。

除了 `netfilter`，剩下的路由则由 Linux 的路由模块处理，对应的命令行工具著名的有 `iproute2`。在上图的 “forward” 和 “route” 处，会根据当前系统的路由表进行路由，选择发送给本机，还是发送给下一跳。“forward” 处的路由负责收到的 IP 包，“route” 处的路由负责本机生成的 IP 包的路由。这些位置的路由都是根据系统的静态路由表和启用的路由算法去选择下一跳，并要求二层发送。路由表可以通过 `iproute2` 和 `route` 配置。

## 2 使用 iptables

### 拒绝来自某一特定 IP 地址的访问

往 `filter table` 中配置，在 `INPUT chain` 中把特定 IP 的包全部 drop 就可以了。例如要拒绝来自 `172.16.6.205` 的访问，

```bash
iptables -t filter -A INPUT -s 172.16.6.205 -j DROP
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/iptables1.png?raw=true)

### 拒绝来自某一特定 MAC 地址的访问

可以利用 `iptables` 的 `mac` 模块。

```bash
iptables -t filter -A INPUT -m mac --mac-source 02:00:46:19:00:03 -j DROP
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/iptables2.png?raw=true)

### 只开放本机的 HTTP 服务，其余协议与端口均拒绝

即只允许 80 端口（不考虑 443）上的 TCP，拒绝其他所有。同时为了方便起见，允许 22 上的 TCP 以便维持 ssh 会话。最后 drop 掉其他所有包。

```bash
iptables -t filter -A INPUT -p tcp -m tcp --dport 80 -j ACCEPT
iptables -t filter -A INPUT -p tcp -m tcp --dport 22 -j ACCEPT
iptables -t filter -A INPUT -j DROP
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/iptables3.png?raw=true)

### 拒绝回应来自某一特定 IP 地址的 ping 命令

在 `OUTPUT` 丢弃所有类型为 0 的 ICMP 包即可。

```bash
iptables -t filter -A OUTPUT -p icmp --icmp-type 0 -d 172.16.6.205 -j DROP
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/iptables4.png?raw=true)

## 3 解释 Linux 网络设备的工作原理

### bridge

bridge 就是现实世界中的交换机。各种网络设备都可以 attach 到 bridge，相当于连上交换机。每次有 Ethernet 帧从某网络设备收到，如果它 attach 到了某个 bridge，那 kernel 会把这一帧首先发送给 bridge，然后 bridge 像普通交换机一样，查询内部的 MAC 端口对应，然后把帧转发给对应的设备。

bridge 还隐式地包含一个和本机连接的端口，在本机上就显示为对应的 bridge 网络设备，例如 `bridge0`。在三层上，每一个 attach 到 bridge 的设备都要把 IP 地址“交给” bridge 管理。若 attach 在上面的设备依然拥有地址，网络包就无法进入 kernel 并传给 bridge 了。此时需要 bridge 来响应 ARP 请求，而不是 attach 在上面的设备。

### vlan

Linux 的 vlan 设备可以类比为真实的 VLAN 交换机。vlan 设备的母设备（例如 `eth0`）下面由多个子设备，每个对应一个 VLAN ID，就像把 VLAN 交换机上的端口按照 PVID 成组，每一组对应 vlan 设备的一个子设备。在母设备 `eth0` 收到 Ethernet 数据帧时，它开始检查 VLAN tag。若没有 VLAN tag，则直接从 `eth0` 传递给 kernel 三层。若含有 VLAN tag（例如 3），则传递给 `eth0.3` 接收。从子设备（例如 `eth0.3`）要发送数据时，实际上会从 `eth0` 发出，但发出之前会打上 VLAN tag 3。总的来说，就是给 Linux Ethernet 网络设备增加了收发带 VLAN tag 的 Ethernet 帧的能力，使其能够配合上层带 VLAN 功能的交换机、路由器使用。

### veth

相当于一根普通的网线（以及对应的虚拟网卡）。从一端进入的包会从另一端出来。用户对它不能进行配置（因为就是一根普通的网线），但是可以把它 attach 到别的设备上，例如两端分别 attach 一个 bridge 上，这样就连接了这两个 bridge。

## 4 解释 Calico 容器网络中数据收发

Calico 比较像一个对路由表和 Linux 防火墙的高层抽象和配置管理、分发系统。在每一台 container host 上运行的 Felix 负责把下发的配置写入当前系统的路由表和防火墙。etcd 负责存储整个网络拓扑等 metadata，作为各个 Felix 配置信息的来源。另外，Calico 采用 BGP 协议，所以每台 host 上还需要 BGP 客户端，与 peer 之间交换信息。

一个 Workload 要发送数据时，无论它发送的 IP 包目的地是哪里，首先都会发送到 host。由于每一个 container 都会通过某种方式（例如 veth attach 到一个 bridge）连接到 host，都会在三层经过一次 host，Felix 在配置路由表的时候就强行将 container 来的包第一跳设为 host，让 host 决定包后面的去向。事实上，host 会通过 BGP 与 peer 交换信息，然后计算出下一跳。IP 包在 host 之间传递，到达目的地 workload 所在的 host 之后，会被 Linux 再次路由，此时 Felix 配置了该 host 的路由表，使得这个 IP 包被发往目的地 workload 对应的虚拟 interface，这个 IP 包就到达了目的地。

## 5 与别的容器组网解决方案对比（Docker swarm overlay）

Swarm 的模式比较像工作在 L2 的 VPN，它自行设计一个方法，把容器的二层数据帧直接封装在 host 的 IP 包中。容器要发送数据帧时，会在 host 被捕获，然后 host 查看这个数据帧目标的 MAC 地址，并查询映射关系，找到这一 MAC 地址对应的容器的 host。之后，这一数据帧封装进 host 的 iP 包中，并往刚刚查询到的 host 发送。之后的发送完全在物理网络上进行。IP 包到达对面 host 之后，host 检查其内容，发现是 overlay 网络的数据，之后将其打开，并按照 MAC 地址发送给对应的容器。在容器看来，互相之间是完全处于同一个二层网络下的。

它和 Calico 的区别在于，Calico 没有做任何“虚拟化”，container 出来包最多只是被改写目的地等信息，本身没有被二次封装，而是直接在物理网络中被路由；相比，Overlay 相当于在物理网络上通过把数据帧封装进 IP 包中，就像创建了一个集中控制的 VPN 之中的网络。可以预期 Calico 的模式的 overhead 较小，同等条件下性能较好。而 Overlay 由于将 container 的数据直接封装， host 之间的路由完全不会去改动，因此较为灵活，且无需改动 host 的路由表，出错几率小，系统较清晰简单；另外直接在二层虚拟化，允许 container 直接使用依赖二层的服务，例如利用 samba 这类要求同属于同一二层网络的协议。总的来看，Calico 和 Overlay 对于容器网络的实现，分别用类 NAT 和 VPN 的概念。Calico 致力于利用现有协议，通过修改物理网络的路由表，使得容器之间的 IP 包可以准确路由；通过修改 Linux 的防火墙，实现 ACL。Overlay 更像直接用 VPN 将容器之间连接，在物理网络上虚拟出一个网络，容器网络内部的二层、三层数据传输都是和 host 间物理网络完全隔开的。

对于其他实现，Calico 和 Overlay 比较相似，例如都用了分布式键值存储使得网络 metadata 一致且可靠、都提供强大的 ACL 控制、都支持超大规模等。

## 6 部署 Jupyter Notebook

本次实验使用两台机器（`mesos3` 和 `mesos2`） 。先部署 Calico。按照项目网站文档，首先安装 etcd。直接下载 build 好的 binary，简单又粗暴。

```bash
wget https://github.com/coreos/etcd/releases/download/v3.1.7/etcd-v3.1.7-linux-amd64.tar.gz
tar xf etcd-v3.1.7-linux-amd64.tar.gz
cd etcd-v3.1.7-linux-amd64
sudo cp etcd* /usr/local/bin
```

然后分别启动两台机器上的 etcd，

```bash
mesos3$ etcd --name mesos3 --initial-advertise-peer-urls http://172.16.6.107:2380\
--listen-peer-urls http://172.16.6.107:2380\
--listen-client-urls http://172.16.6.107:2379,http://127.0.0.1:2379\
--advertise-client-urls http://172.16.6.107:2379\
--initial-cluster-token mesos\
--initial-cluster mesos3=http://172.16.6.107:2380,mesos2=http://172.16.6.205:2380\
--initial-cluster-state new
mesos2$ etcd --name mesos2 --initial-advertise-peer-urls http://172.16.6.205:2380\
--listen-peer-urls http://172.16.6.205:2380\
--listen-client-urls http://172.16.6.205:2379,http://127.0.0.1:2379\
--advertise-client-urls http://172.16.6.205:2379\
--initial-cluster-token mesos\
--initial-cluster mesos3=http://172.16.6.107:2380,mesos2=http://172.16.6.205:2380\
--initial-cluster-state new
```

进程会一直运行。从当前的 tmux session detach 即可。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-5/attachments/etcd1.png?raw=true)

然后需要让 docker daemon 使用 etcd。直接去修改 docker 的 systemd service unit，把 systemd 里启动 `dockerd` 的命令改了就行。

```bash
sudo sed -i '/ExecStart=\/usr\/bin\/dockerd -H fd:\/\//c\ExecStart=\/usr\/bin\/dockerd --cluster-store etcd:\/\/127.0.0.1:2379 -H fd:\/\/' /etc/systemd/system/multi-user.target.wants/docker.service
sudo systemctl restart docker
```

接下来安装 Calico CLI tool，

```bash
sudo wget -O /usr/local/bin/calicoctl http://www.projectcalico.org/builds/calicoctl
sudo chmod +x /usr/local/bin/calicoctl
```

然后用它直接启动 Calico。会自动下载需要的 docker image。

```bash
mesos2$ sudo calicoctl node run --ip 172.16.6.205 --name mesos2
mesos3$ sudo calicoctl node run --ip 172.16.6.107 --name mesos3
```

