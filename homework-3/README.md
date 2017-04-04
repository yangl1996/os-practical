# 第三次作业

## 1 安装配置 Docker

在 Ubuntu 16.04 中，直接添加 Docker 提供的源，并更新 aptitude 的包 index，然后直接安装 Docker CE。

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update
sudo apt-get install docker-ce
```

## 2 Docker 基本命令介绍

### `docker pull`

从 Docker Hub（或第三方源）拉取镜像。

命令用法：`docker pull [OPTIONS] NAME[:TAG|@DIGEST]`

`TAG` 是要拉取镜像的版本号或版本名。`DIGEST` 是镜像的哈希，用于防止篡改或下载到错误的镜像。`NAME` 是要拉取镜像的名称。

`OPTION` 可以设一些选项。`-a` 或 `--all-tags` 下载对应镜像的所有版本。`--disable-content-trust` 不校验哈希（这个选项默认是开启的）。

使用例子：`docker pull debian:jessie`，拉取 Debian 8。

### `docker images`

列出系统中当前存在的镜像。

命令用法：`docker images [OPTIONS] [REPOSITORY[:TAG]]`

`REPOSITORY` 可以指定只列出某一个仓库的镜像。`TAG` 可以进一步指定只列出某一版本。

`OPTION` 支持的选项有：`-a` 列出所有镜像（包括中间层——Docker 镜像可以依赖于别的镜像，从而避免重复占用空间）；`--digests` 列出哈希；`--format` 对输出格式化；`--no-trunc` 列出所有字段全部内容；`-q` 只显示数字 ID，便于作为其他命令的参数传入；`-f` 按条件过滤输出。

使用例子：`docker images java:8`，列出 Java 8 的镜像。

### `docker run`

启动一个 Docker 容器。

命令用法：`docker run [OPTIONS] IMAGE[:TAG|@DIGEST] [COMMAND] [ARG...]`

`IMAGE[:TAG|@DIGEST]` 指定镜像名（或 ID），以及可通过指定版本和哈希值精确匹配。`COMMAND` 指定容器起来之后执行的命令。`ARG...` 指定 `COMMAND` 要带的参数。

该命令是 Docker 相当核心的命令，选项众多，翻译 manpage 意义不大，所以列举部分参数。可用选项包括但不限于：

* `-d`，从当前 shell detach
* `--network`，设置 attach 到哪一个网络
* `--restart`，设置重启条件
* `--name`，设置容器名字
* `--device`，设置外设穿透
* `-e`，设置容器里的环境变量
* `--volumes-from`，从别的容器挂载 data volume
* `--volume`，从某路径挂载 data volume

使用例子：`docker run --name blog --volumes-from ghoststore --net=blog_isolated -e "NODE_ENV=production" -d ghost`，（在转向 LXC 之前）我用这个命令启动[我的博客](https://blog.yangl1996.com/update-ghost-running-on-docker/)。主要设置了容器名字、挂载 Data Volume Container、attach 到网络、设置环境变量、设置从当前 shell detach。

### `docker network`

`docker network` 有多个子命令：

* `connect` 将容器连接到一个网络
* `create` 创建一个网络
* `disconnect` 将容器从一个网络断开
* `inspect` 输出详细信息
* `ls` 列出所有网络
* `prune` 删除所有不用的网络
* `rm` 删除某个网络

下面简介 `docker network create`。

命令用法：`docker network create [OPTIONS] NETWORK`

`NETWORK` 是要创建的网络的名字。`OPTIONS` 提供以下选项：

* `--attachable` 允许手动将容器 attach 到该网络
* `--aux-address` 该网络的地址（和 Linux bridge 的地址一个概念）
* `-d` 网络的类型
* `--gateway` 该网络的默认网关
* `--ip-range` 该网络可分配的地址段

翻译 manpage 意义不大，暂时列出这些。

再介绍一个 `docker network connect` 的用法。

命令用法：`docker network connect [--help] NETWORK CONTAINER`

`NETWORK` 和 `CONTAINER` 分别表示要把哪个容器 attach 到哪个网络。

用法例子：`docker network connect multi-host-network container1`

### `docker ps`

类似 shell 的 `ps` 命令，列出存在的容器。

提供如下选项（`docker images` 里有过的不列了）：

* `--latest`，只显示最近创建的容器
* `-n`，列出最近创建的 n 个容器
* `-s`，列出容器总大小

## 创建 Nginx 镜像

首先写一个 Dockerfile，内容如下

```Dockerfile
FROM ubuntu:xenial
RUN apt -y update && apt install -y nginx
RUN echo 'Lei Yang, 1400012791' > /var/www/html/index.html
CMD tail -f /var/log/nginx/access.log
```

主要就是安装，然后往默认页面里写学号和姓名，然后不断输出 log。

然后在当前目录运行

```bash
sudo docker build -t basic-nginx .
```

以 build 这个镜像。完成后，镜像就在本地可用了。下面创建网络。

```bash
sudo docker network create --driver bridge docker-internal
```

之后执行

```bash
sudo docker run --network=docker-internal --name=dummy-nginx basic-nginx nginx -g 'daemon off;'
```

此时 `docker inspect`，可以看到容器在 `docker-internal` 这个 bridge 上的 IP 地址，在我这里的情况是 `172.18.0.2`。查看宿主机网络设备可以看到，出现了 `172.18.0.1` 的网桥。事实上，此时宿主机已经可以访问容器。

![ss](https://github.com/yangl1996/os-practical/blob/master/homework-3/attachments/1.png?raw=true)
