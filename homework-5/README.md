# 第五次作业

## 描述 Linux 内核对 IP 数据包的处理

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

## 使用 `iptables`

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

## 解释 Linux 网络设备的工作原理
