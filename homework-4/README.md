# 第四次作业

## 调研两种分布式文件系统和一种联合文件系统

### GlusterFS

#### 工作原理

Server 端，每一台 server 上跑一个 `glusterfsd`，有很多 storage brick。它把本地文件系统的一部分作为一个 volume 暴露给 clients。Client 上运行的 `glusterfs` 去连接这些 volume，它们之间的通信用的是 GlusterFS 自定的一个协议，可以跑在 TCP、Infiniband 等很多传输层上。在 client，一系列 translator 把这些 volume 中的 brick 一步步（处理协议通信、处理冗余、将文件操作 map 到合适的 brick 等）合并抽象成一个完整的文件系统，最后用 FUSE 挂载在 client 的 rootfs 里，client 上的程序就可以访问这个文件系统了。

事实上，GlusterFS 将主要的功能抽象、模块化成一个个 translator。要改功能、增加功能，只要改对应的 translator。例如，想改变文件如何 map 到 brick，只要去修改做这件事的 translator。想改变 server 端数据存储方法，也只需要修改 translator，在 translator 这边修改 GlusterFS 中文件如何存储到服务器上 bare-metal 的文件系统。正因如此，server 端的设计可以很简单，因为它几乎不需要任何逻辑，只需要把本地的文件系统（如一个目录）用 GlusterFS 的协议暴露给外界，供 client 访问即可。它事实上只是 client 访问 server 上文件系统的一个代理。

Volume 的安排和组织可以很灵活，例如，1、2 之间互相备份，3、4 直接互相备份，然后 12、34 两组合并为一个虚拟的文件系统，暴露给终端用户。这一切映射都是在 client 端完成的。可以想见，对于超大型的集群、超复杂的虚拟文件系统，client 机器需要很强的计算能力，才能快速完成这一文件到具体 server、brick 的映射工作。我认为，这一定程度上限制了 GlusterFS 的 scalability。

#### 使用方式

在服务器端，首先所有 server 互相确认，形成一个 storage pool。然后为 storage brick 创建一个路径。然后在其中一台上起一个 volume 即可。

```bash
# on server 1
gluster peer probe server2 # prove server 2. do the same on server 2
mkdir -p /data/brick1/gv0 # do the same on server 2
gluster volume create gv0 replica 2 server1:/data/brick1/gv0 server2:/data/brick1/gv0
gluster volume start gv0
```

在客户端，直接挂载即可。

```bash
# on client
mount -t glusterfs server1:/gv0 /mnt
```

### HDFS

#### 工作原理

一个 HDFS 集群有一个 NameNode（fail 了怎么办？可以用 ZooKeeper 做热备吗？貌似不行。），用来存放整个文件系统的 metadata，同时控制 client 对整个文件系统的访问。另外，剩下来每一个节点叫 DataNode，顾名思义存放实际数据的。一个文件在 HDFS 中会被分成多个 block，分散存储在各个 DataNode 上。NameNode 维护这一文件与 DataNode 之间的映射关系。用户在访问文件时，先请求 NameNode 打开文件，并获知这个文件对应哪几个 block，然后直接联系 DataNode 去对 block 进行读写。可以发现，NameNode 事实上是整个 HDFS 的唯一中心，所以为了挽救 HDFS 的 scalability，可以把关键的 metadata 放进 memory 里提高性能。而对于 DataNode，它所做的只是向用户提供文件读写，它本身是不知道存了什么文件的，它只知道自己有哪几个 block，提供给 client 的服务也是具体 block 的读写。

使用时，HDFS 可以通过一系列 API 直接在程序中访问，也可以用 FUSE 等方法挂载。

#### 使用方式

1. 设置 DataNode，创建要存放数据的路径，然后改 Hadoop 的配置文件，使用这一路径
2. 设置 NameNode，生成 metadata 数据库
3. 配置其他功能，如 load balancing、NameNode 的 snapshot 等
4. 启动 HDFS 服务

### OverlayFS

#### 工作原理

OverlayFS 是一个联合文件系统。它的目的就是把来自多个目录或文件系统的内容叠加起来，给终端用户呈现为一整个文件系统。例如，两个文件系统都有 `/etc/systemd` 目录，OverlayFS 可以把其中一个叠放在另一个上面，对于上层拥有的文件，直接将上层的文件呈现给用户；对上层没有但下层有的文件，则把下层的文件呈现给用户，也就是说将讲个目录合并成一个，并优先呈现上层的文件。在写入时，对上层的文件直接写入，对来自下层的文件进行 CoW。另外，OverlayFS 会对合并之后的文件系统的文件列表做一个 cache，加快列出目录中所有文件这一类操作的速度。

#### 使用方式

```bash
mount -t overlay overlay -o lowerdir=/lower,upperdir=/upper,workdir=/work /merged
```

`workdir` 用于在操作中暂存文件使用。它必须是上层文件系统中的一个空目录。

## 安装配置一种分布式文件系统

选择 GlusterFS。首先安装打包好的 GlusterFS，

```bash
sudo pacman -S glusterfs
```

虽然 rpcbind 写着是 recommended dependency，但是发现不装的话，systemd unit 起不来，所以还是装一下，

```bash
sudo pacman -S rpcbind
```

然后就可以把 GlusterFS 的 daemon 起来了，

```bash
sudo systemctl start glusterd.service
```

两台机器互相 probe，形成一个 trusted pool，并在两边分别新建目录，准备存放数据

```bash
node1$ sudo gluster peer probe 172.16.6.107
node1$ mkdir gfsbrick
node3$ sudo gluster peer probe 172.16.6.234
node3$ mkdir gfsbrick
```

为了满足要求的容错性能，这里用 replica 模式创建 Volume，这样其中一个机器 down 掉了，由于数据一直互相镜像，因此所有数据依然是可用的。由于 GlusterFS 推荐不要在 root 分区存数据，默认是不允许这么做的，因此需要加上 `force` 选项。

```bash
node1$ sudo gluster volume create gv0 replica 2\
         172.16.6.234:/home/yangl1996/gfsbrick\
         172.16.6.107:/home/pkusei/gfsbrick force
volume create: gv0: success: please start the volume to access data
```

最后启动这个新建的 volume，

```bash
sudo gluster volume start gv0
```

就可以了。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/gluster1.png?raw=true)

然后，可以尝试在第三台机器上挂载这个文件系统，并测试一般的读写操作。

```bash
node2$ mkdir gfsmountpoint
node2$ sudo mount -t glusterfs 172.16.6.234:/gv0 /home/pkusei/gfsmountpoint
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/gfsmount.png?raw=true)

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/gfsrwtest.png?raw=true)

为了测试其容错性，故意关掉一台机器的 GlusterFS Server daemon。

```bash
node3$ sudo systemctl stop glusterd.service
```

然后再去测试，发现依然可以读写，也可以正常读写之前的文件，说明文件系统在损失一个节点后依然完好。

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/gfstest.png?raw=true)

## Docker 里挂载 GlusterFS

稍微修改上次作业用的 Dockerfile，在建立时多装一个 `glusterfs-client`。改好是这样的：

```Docker
FROM ubuntu:xenial
RUN apt -y update && apt install -y nginx glusterfs-client
CMD mkdir /gfsmountpoint && mount -t glusterfs 172.16.6.234:/gv0 /gfsmountpoint && cp /gfsmountpoint/index.html /var/www/html/index.html && nginx -g 'daemon off;'
```

`CMD` 是 `docker run` 时缺省执行的命令，在这里是依次建立挂载点、挂载 GlusterFS、把文件拷到 `www-root`，然后启动 Nginx。

然后启动容器。为了执行挂载命令，需要用 `--privileged` 开启特权模式。

```bash
sudo docker build -t basic-nginx .
sudo docker run -p 80:80 --name nginx-instance --privileged -d basic-nginx
```

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/glusterwebpage.png?raw=true)

## 用联合文件系统制作 Docker 镜像

Docker 的镜像基于联合文件系统，由一层层叠加起来，最底层是基础的 rootfs（默认是 Alpine Linux 的 rootfs），然后在上面作修改，实现不同功能，然后叠加起来。例如，安装软件包时，对 rootfs 做了修改，这个修改就被存在一层中。在不同镜像之间，可以共享层，例如，机器上有两个基于 Alpine Linux 的镜像，那它们是可以共享最底下 Alpine Linux rootfs 那层的。当从镜像启动一个新的容器时，会在上面再叠加一层，读写就通过这一层进行。

首先新建一个容器，并将其启动，

```bash
sudo docker create -it --name myalpine alpine /bin/sh
sudo docker start -i myalpine
```

查看当前文件系统的各层。本来容器的文件系统的挂载点就是容器的 ID，现在不是了。为确定挂载点，先停止其他所有容器，然后看当前系统所有挂载的 aufs。

```bash
sudo su -
df -T | grep aufs
```

只有一条记录，就是当前跑者的 container。

```
none                         aufs            18982780 6138856  11856584  35% /var/lib/docker/aufs/mnt/5ffa44145194ae7e175e5b6d1b1990337ab7989bb5ea8054e21effe264536d03
```

然后就可以看这个 container 文件系统的组成了。

```bash
cd /var/lib/docker/aufs
cat layer/5ffa44145194ae7e175e5b6d1b1990337ab7989bb5ea8054e21effe264536d03
```

可以看到下面还有两层：

```
5ffa44145194ae7e175e5b6d1b1990337ab7989bb5ea8054e21effe264536d03-init
ad000efeb87b182ac9651ecd70d84d88ea0a9ce6f7d7263b65cd8f6cf0e08754
```

`xxx-init` 这一层存放一些配置，例如 `/etc/hostname`；最下面一层就是 Alpine Linux 的 bashimg，把它拷出来。

```bash
cp -r ad000efeb87b182ac9651ecd70d84d88ea0a9ce6f7d7263b65cd8f6cf0e08754 /home/pkusei/baseimg
```

然后在 container 里面装点包，

```sh
apk update
apk add wget
```

再把最上面的拷出来。`xxx-init` 不拷无所谓，反正最后新建 container 的时候还会加这么一层。

```bash
cp -r 5ffa44145194ae7e175e5b6d1b1990337ab7989bb5ea8054e21effe264536d03 /home/pkusei/containerlayer
```

然后开始把两个 layer 叠起来，

```bash
mkdir fullimg
sudo mount -t aufs -o br=/home/pkusei/baseimg=ro:/home/pkusei/containerlayer=ro none /home/pkusei/fullimg
```

然后把这个文件系统打包，再用 `docker import` 创建新镜像，

```bash
$ sudo tar -c fulimg > /home/pkusei/fullimg.tar
$ sudo docker import fullimg.tar
sha256:b558faa81cbff383be81d7556fbb42aa85ad0d87ea4e3a8bc4f4fa7eb13bee04
```

最后启动这个镜像，试一试

```bash
sudo docker run -it b558faa81c /bin/sh
```

可以发现已经可以用 `wget` 了：

![gluster1](https://github.com/yangl1996/os-practical/blob/master/homework-4/attachments/createimg.png?raw=true)
